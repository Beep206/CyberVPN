#![forbid(unsafe_code)]

use bytes::{Buf, Bytes};
use ed25519_dalek::pkcs8::EncodePrivateKey;
use h3::quic::{RecvStream as H3RecvStream, SendStream as H3SendStream};
use h3::{client, server};
use h3_datagram::datagram_handler::HandleDatagramsExt;
use h3_quinn::Connection as H3QuinnConnection;
use http::{Response, StatusCode};
use ns_auth::{MintedTokenRequest, SessionTokenSigner};
use ns_carrier_h3::{
    H3ConnectBackoff, H3DatagramRollout, H3RequestKind, H3TransportConfig, H3ZeroRttPolicy,
    build_client_tls_config_with_roots, build_quinn_transport_config, decode_tunnel_frame,
    recv_h3_associated_udp_datagram, select_h3_udp_flow_for_config,
    send_h3_associated_udp_datagram,
};
use ns_core::{
    Capability, CarrierKind, CarrierProfileId, DatagramMode, DeviceBindingId, ManifestId,
    ProtocolErrorCode, SessionMode, TransportMode,
};
use ns_gateway_runtime::{GatewayPreAuthBudgets, GatewayPreAuthGate, admit_client_hello};
use ns_testkit::{
    FIXTURE_TOKEN_KEY_ID, UdpWanLabProfileId, fixture_token_signing_key, fixture_token_verifier,
    sample_client_hello, udp_wan_lab_profile,
};
use ns_wire::{
    DatagramFlags, FlowFlags, Frame, TargetAddress, UdpDatagram, UdpFlowClose, UdpFlowOpen,
    UdpStreamClose, UdpStreamOpen, UdpStreamPacket,
};
use quinn::crypto::rustls::{QuicClientConfig, QuicServerConfig};
use quinn::{ClientConfig, Endpoint, ServerConfig};
use rcgen::generate_simple_self_signed;
use rustls::RootCertStore;
use rustls::pki_types::{CertificateDer, PrivatePkcs8KeyDer};
use std::collections::{BTreeMap, BTreeSet};
use std::future::Future;
use std::future::poll_fn;
use std::io;
use std::net::{Ipv4Addr, SocketAddr};
use std::sync::{Arc, Mutex};
use std::time::Duration as StdDuration;
use time::{Duration, OffsetDateTime};
use tokio::net::UdpSocket;
use tokio::task::JoinHandle;
use tokio::time::timeout;
use tracing_subscriber::fmt::MakeWriter;

fn transport_config(
    datagram_enabled: bool,
    datagram_rollout: H3DatagramRollout,
) -> H3TransportConfig {
    H3TransportConfig {
        carrier_kind: CarrierKind::H3,
        carrier_profile_id: CarrierProfileId::new("carrier-primary")
            .expect("fixture carrier profile should be valid"),
        origin_host: "localhost".to_owned(),
        origin_port: 443,
        sni: Some("localhost".to_owned()),
        alpn: vec!["h3".to_owned()],
        control_path: "/ns/control".to_owned(),
        relay_path: "/ns/relay".to_owned(),
        headers: BTreeMap::from([
            ("x-verta-profile".to_owned(), "carrier-primary".to_owned()),
            ("x-verta-phase".to_owned(), "milestone-14".to_owned()),
        ]),
        datagram_enabled,
        datagram_rollout,
        heartbeat_interval_ms: 20_000,
        idle_timeout_ms: 90_000,
        zero_rtt_policy: H3ZeroRttPolicy::Disabled,
        connect_backoff: H3ConnectBackoff {
            initial_ms: 500,
            max_ms: 10_000,
            jitter: 0.2,
        },
    }
}

#[derive(Clone, Default)]
struct TestLogSink(Arc<Mutex<Vec<u8>>>);

struct TestLogWriter(Arc<Mutex<Vec<u8>>>);

impl io::Write for TestLogWriter {
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        self.0
            .lock()
            .expect("test log sink poisoned")
            .extend_from_slice(buf);
        Ok(buf.len())
    }

    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}

impl<'a> MakeWriter<'a> for TestLogSink {
    type Writer = TestLogWriter;

    fn make_writer(&'a self) -> Self::Writer {
        TestLogWriter(self.0.clone())
    }
}

async fn capture_logs_async<T>(future: impl Future<Output = T>) -> (T, String) {
    let sink = TestLogSink::default();
    let subscriber = tracing_subscriber::fmt()
        .with_writer(sink.clone())
        .with_ansi(false)
        .without_time()
        .json()
        .finish();
    let dispatch = tracing::Dispatch::new(subscriber);
    let guard = tracing::dispatcher::set_default(&dispatch);
    let result = future.await;
    drop(guard);
    let bytes = sink.0.lock().expect("test log sink poisoned").clone();
    let output = String::from_utf8(bytes).expect("captured tracing output should be UTF-8");
    (result, output)
}

fn assert_datagram_transport_selected_without_fallback(logs: &str, label: &str) {
    assert!(
        logs.contains("\"event_name\":\"verta.carrier.datagram.selection\""),
        "{label} should emit a datagram selection event",
    );
    assert!(
        logs.contains("\"selection\":\"datagram\""),
        "{label} should keep datagrams selected",
    );
    assert!(
        !logs.contains("\"selection\":\"stream_fallback\""),
        "{label} must not silently fall back after datagrams were selected",
    );
}

fn assert_datagram_lab_profile_keeps_selected_transport(
    logs: &str,
    profile_id: UdpWanLabProfileId,
) {
    let profile = udp_wan_lab_profile(profile_id);
    assert_datagram_transport_selected_without_fallback(logs, profile.slug);
}

fn mint_token(now: OffsetDateTime) -> String {
    let private_key_pem = fixture_token_signing_key()
        .to_pkcs8_pem(Default::default())
        .expect("fixture token signing key should encode");
    SessionTokenSigner::from_ed_pem(
        "bridge.example",
        "verta-gateway",
        FIXTURE_TOKEN_KEY_ID,
        private_key_pem.as_bytes(),
    )
    .expect("fixture signer should initialize")
    .mint(
        MintedTokenRequest {
            subject: "acct-1".to_owned(),
            device_id: DeviceBindingId::new("device-1").expect("fixture device id should be valid"),
            manifest_id: ManifestId::new("man-2026-04-01-001")
                .expect("fixture manifest id should be valid"),
            policy_epoch: 7,
            core_versions: vec![1],
            carrier_profiles: vec!["carrier-primary".to_owned()],
            capabilities: vec![Capability::TcpRelay.id(), Capability::UdpRelay.id()],
            session_modes: vec!["tcp".to_owned()],
            region_scope: None,
            token_max_relay_streams: Some(16),
            token_max_udp_flows: Some(4),
            token_max_udp_payload: Some(1200),
        },
        now,
        Duration::seconds(300),
    )
    .expect("fixture token should mint")
    .token
}

fn make_server_endpoint(config: &H3TransportConfig) -> (Endpoint, CertificateDer<'static>) {
    let cert = generate_simple_self_signed(vec!["localhost".into()])
        .expect("localhost certificate should generate");
    let cert_der = cert.cert.der().clone();
    let key_der = PrivatePkcs8KeyDer::from(cert.signing_key.serialize_der());

    let mut tls = rustls::ServerConfig::builder()
        .with_no_client_auth()
        .with_single_cert(vec![cert_der.clone()], key_der.into())
        .expect("server TLS config should initialize");
    tls.alpn_protocols = config
        .alpn
        .iter()
        .map(|value| value.as_bytes().to_vec())
        .collect();

    let mut server_config = ServerConfig::with_crypto(Arc::new(
        QuicServerConfig::try_from(tls).expect("quic server config should initialize"),
    ));
    server_config.transport =
        Arc::new(build_quinn_transport_config(config).expect("transport config should be valid"));
    let endpoint = Endpoint::server(server_config, SocketAddr::from((Ipv4Addr::LOCALHOST, 0)))
        .expect("server endpoint should bind");

    (endpoint, cert_der)
}

fn make_client_endpoint(config: &H3TransportConfig, cert_der: CertificateDer<'static>) -> Endpoint {
    let mut roots = RootCertStore::empty();
    roots
        .add(cert_der)
        .expect("generated server certificate should be trusted");
    let tls = build_client_tls_config_with_roots(config, roots)
        .expect("client TLS config should initialize");
    let client_config = ClientConfig::new(Arc::new(
        QuicClientConfig::try_from(tls).expect("quic client config should initialize"),
    ));
    let mut endpoint = Endpoint::client(SocketAddr::from((Ipv4Addr::LOCALHOST, 0)))
        .expect("client endpoint should bind");
    endpoint.set_default_client_config(client_config);
    endpoint
}

async fn start_udp_echo_server() -> (SocketAddr, JoinHandle<()>) {
    let socket = UdpSocket::bind(SocketAddr::from((Ipv4Addr::LOCALHOST, 0)))
        .await
        .expect("UDP echo server should bind");
    let addr = socket
        .local_addr()
        .expect("UDP echo server should have a local address");
    let task = tokio::spawn(async move {
        let mut buffer = [0_u8; 1500];
        while let Ok((read, peer)) = socket.recv_from(&mut buffer).await {
            if socket.send_to(&buffer[..read], peer).await.is_err() {
                break;
            }
        }
    });
    (addr, task)
}

fn localhost_target(port: u16) -> UdpFlowOpen {
    UdpFlowOpen {
        flow_id: 7,
        target: TargetAddress::Ipv4(Ipv4Addr::LOCALHOST.octets()),
        target_port: port,
        idle_timeout_ms: 15_000,
        flags: FlowFlags::new(0b0011).expect("fixture udp flow flags should be valid"),
        metadata: Vec::new(),
    }
}

fn datagram_only_target(port: u16) -> UdpFlowOpen {
    UdpFlowOpen {
        flow_id: 11,
        target: TargetAddress::Ipv4(Ipv4Addr::LOCALHOST.octets()),
        target_port: port,
        idle_timeout_ms: 15_000,
        flags: FlowFlags::new(0b0001).expect("datagram-only fixture flags should be valid"),
        metadata: Vec::new(),
    }
}

fn udp_socket_addr(target: &TargetAddress, port: u16) -> SocketAddr {
    match target {
        TargetAddress::Ipv4(bytes) => SocketAddr::from((*bytes, port)),
        other => panic!("test only supports ipv4 UDP targets, got {other:?}"),
    }
}

async fn recv_server_frame<S>(stream: &mut server::RequestStream<S, Bytes>, label: &str) -> Frame
where
    S: H3RecvStream + H3SendStream<Bytes> + Send,
{
    let mut payload = stream
        .recv_data()
        .await
        .unwrap_or_else(|error| panic!("{label} should be readable: {error}"))
        .unwrap_or_else(|| panic!("{label} should contain a frame"));
    let bytes = payload.copy_to_bytes(payload.remaining());
    decode_tunnel_frame(bytes.as_ref())
        .unwrap_or_else(|error| panic!("{label} should decode as a tunnel frame: {error}"))
}

async fn send_server_frame<S>(
    stream: &mut server::RequestStream<S, Bytes>,
    frame: &Frame,
    label: &str,
) where
    S: H3RecvStream + H3SendStream<Bytes> + Send,
{
    stream
        .send_data(
            ns_carrier_h3::encode_tunnel_frame(frame)
                .unwrap_or_else(|error| panic!("{label} should encode: {error}")),
        )
        .await
        .unwrap_or_else(|error| panic!("{label} should send: {error}"));
}

async fn recv_client_frame<S>(stream: &mut client::RequestStream<S, Bytes>, label: &str) -> Frame
where
    S: H3RecvStream + H3SendStream<Bytes> + Send,
{
    let mut payload = stream
        .recv_data()
        .await
        .unwrap_or_else(|error| panic!("{label} should be readable: {error}"))
        .unwrap_or_else(|| panic!("{label} should contain a frame"));
    let bytes = payload.copy_to_bytes(payload.remaining());
    decode_tunnel_frame(bytes.as_ref())
        .unwrap_or_else(|error| panic!("{label} should decode as a tunnel frame: {error}"))
}

async fn send_client_frame<S>(
    stream: &mut client::RequestStream<S, Bytes>,
    frame: &Frame,
    label: &str,
) where
    S: H3RecvStream + H3SendStream<Bytes> + Send,
{
    stream
        .send_data(
            ns_carrier_h3::encode_tunnel_frame(frame)
                .unwrap_or_else(|error| panic!("{label} should encode: {error}")),
        )
        .await
        .unwrap_or_else(|error| panic!("{label} should send: {error}"));
}

fn finish_or_allow_h3_no_error<E: std::fmt::Display>(result: Result<(), E>, label: &str) {
    if let Err(error) = result {
        let message = error.to_string();
        if !message.contains("H3_NO_ERROR") && !message.contains("0x0") {
            panic!("{label}: {message}");
        }
    }
}

async fn settle_h3_driver_or_abort(drive_task: &mut JoinHandle<()>) {
    if tokio::time::timeout(StdDuration::from_millis(500), &mut *drive_task)
        .await
        .is_err()
    {
        drive_task.abort();
        let _ = drive_task.await;
    }
}

#[tokio::test]
async fn loopback_h3_datagrams_round_trip_after_udp_flow_open() {
    let (result, logs) = capture_logs_async(timeout(StdDuration::from_secs(10), async {
        let config = transport_config(true, H3DatagramRollout::Automatic);
        let (server_endpoint, cert_der) = make_server_endpoint(&config);
        let server_addr = server_endpoint
            .local_addr()
            .expect("server endpoint should have a local address");
        let client_endpoint = make_client_endpoint(&config, cert_der);
        let server_config = config.clone();
        let client_config = config.clone();
        let (echo_addr, echo_task) = start_udp_echo_server().await;
        let client_hello =
            Frame::ClientHello(sample_client_hello(mint_token(OffsetDateTime::now_utc())));
        let udp_open = localhost_target(echo_addr.port());

        let server_future = async move {
            let gate = GatewayPreAuthGate::new(GatewayPreAuthBudgets::default())
                .expect("default gateway pre-auth budgets should be valid");
            let connecting = server_endpoint
                .accept()
                .await
                .expect("server should accept one connection");
            let connection = connecting
                .await
                .expect("server-side quic connection should establish");
            let mut builder = server::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(true);
            let mut incoming = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("server h3 connection should initialize");
            let mut datagram_reader = incoming.get_datagram_reader();
            let resolver = incoming
                .accept()
                .await
                .expect("server should accept a control request")
                .expect("server should receive one control request");
            let (_request, mut control_stream) = resolver
                .resolve_request()
                .await
                .expect("control request should resolve");
            let control_stream_id = control_stream.send_id();

            let permit = gate
                .try_begin_hello()
                .expect("control request should fit within pending-hello budgets");
            let hello = match recv_server_frame(&mut control_stream, "control hello").await {
                Frame::ClientHello(hello) => hello,
                other => panic!("expected client hello on control stream, got {other:?}"),
            };
            permit
                .enforce_control_body_size(
                    ns_carrier_h3::encode_tunnel_frame(&Frame::ClientHello(hello.clone()))
                        .expect("hello should re-encode")
                        .len(),
                )
                .expect("hello body should stay within pre-auth limits");
            permit
                .enforce_handshake_deadline()
                .expect("hello should arrive before the handshake deadline");

            let mut outcome = admit_client_hello(
                &fixture_token_verifier(),
                &hello,
                SessionMode::Tcp,
                server_config.advertised_datagram_mode(true),
            )
            .expect("gateway admission should succeed");

            control_stream
                .send_response(
                    Response::builder()
                        .status(StatusCode::OK)
                        .body(())
                        .expect("control response should build"),
                )
                .await
                .expect("control response should send");
            send_server_frame(
                &mut control_stream,
                &Frame::ServerHello(outcome.response.clone()),
                "server hello",
            )
            .await;

            let open = match recv_server_frame(&mut control_stream, "udp-flow-open").await {
                Frame::UdpFlowOpen(open) => open,
                other => panic!("expected udp-flow-open on control stream, got {other:?}"),
            };
            let ok =
                select_h3_udp_flow_for_config(&mut outcome.controller, &open, &server_config, true)
                    .expect("gateway should select datagram mode");
            assert_eq!(ok.transport_mode, TransportMode::Datagram);
            send_server_frame(
                &mut control_stream,
                &Frame::UdpFlowOk(ok.clone()),
                "udp-flow-ok",
            )
            .await;

            let datagram = recv_h3_associated_udp_datagram(
                &mut datagram_reader,
                control_stream_id,
                ok.effective_max_payload as usize,
            )
            .await
            .expect("gateway should receive one associated datagram");
            assert_eq!(datagram.flow_id, open.flow_id);

            let upstream = UdpSocket::bind(SocketAddr::from((Ipv4Addr::LOCALHOST, 0)))
                .await
                .expect("gateway UDP socket should bind");
            upstream
                .send_to(
                    datagram.payload.as_slice(),
                    udp_socket_addr(&open.target, open.target_port),
                )
                .await
                .expect("gateway should send one UDP packet upstream");
            let mut buffer = [0_u8; 1500];
            let (read, _peer) = timeout(StdDuration::from_secs(2), upstream.recv_from(&mut buffer))
                .await
                .expect("gateway should receive an echoed UDP packet before timing out")
                .expect("gateway UDP recv should succeed");

            let mut datagram_sender = incoming.get_datagram_sender(control_stream_id);
            send_h3_associated_udp_datagram(
                &mut datagram_sender,
                &UdpDatagram {
                    flow_id: datagram.flow_id,
                    flags: DatagramFlags::new(0).expect("fixture datagram flags should be valid"),
                    payload: buffer[..read].to_vec(),
                },
                ok.effective_max_payload as usize,
            )
            .expect("gateway should echo the associated datagram");

            let close = match recv_server_frame(&mut control_stream, "udp-flow-close").await {
                Frame::UdpFlowClose(close) => close,
                other => panic!("expected udp-flow-close on control stream, got {other:?}"),
            };
            assert_eq!(close.flow_id, open.flow_id);
            assert_eq!(close.code, ProtocolErrorCode::NoError);
            assert!(outcome.controller.release_udp_flow(open.flow_id));

            finish_or_allow_h3_no_error(
                control_stream.finish().await,
                "control response should finish cleanly",
            );
            server_endpoint.wait_idle().await;
        };

        let client_future = async move {
            let connection = client_endpoint
                .connect(server_addr, "localhost")
                .expect("client connect should start")
                .await
                .expect("client quic connection should establish");
            let mut builder = client::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(false);
            let (mut driver, mut sender) = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("client h3 connection should initialize");
            let mut control_stream = sender
                .send_request(
                    client_config
                        .request_template(H3RequestKind::Control)
                        .expect("control request template should build")
                        .build_request()
                        .expect("control request should build"),
                )
                .await
                .expect("client should open the control request stream");
            let control_stream_id = control_stream.id();
            let mut datagram_reader = driver.get_datagram_reader();
            let mut datagram_sender = driver.get_datagram_sender(control_stream_id);
            let drive_task = tokio::spawn(async move {
                let _ = poll_fn(|cx| driver.poll_close(cx)).await;
            });

            let request_future = async move {
                send_client_frame(&mut control_stream, &client_hello, "client hello").await;
                let response = control_stream
                    .recv_response()
                    .await
                    .expect("control response headers should arrive");
                assert_eq!(response.status(), StatusCode::OK);
                let server_hello =
                    match recv_client_frame(&mut control_stream, "server hello").await {
                        Frame::ServerHello(hello) => hello,
                        other => panic!("expected server hello on control stream, got {other:?}"),
                    };
                assert_eq!(
                    server_hello.datagram_mode,
                    DatagramMode::AvailableAndEnabled
                );

                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowOpen(udp_open.clone()),
                    "udp-flow-open",
                )
                .await;
                let ok = match recv_client_frame(&mut control_stream, "udp-flow-ok").await {
                    Frame::UdpFlowOk(ok) => ok,
                    other => panic!("expected udp-flow-ok on control stream, got {other:?}"),
                };
                assert_eq!(ok.transport_mode, TransportMode::Datagram);

                send_h3_associated_udp_datagram(
                    &mut datagram_sender,
                    &UdpDatagram {
                        flow_id: udp_open.flow_id,
                        flags: DatagramFlags::new(0)
                            .expect("fixture datagram flags should be valid"),
                        payload: b"verta-udp-echo".to_vec(),
                    },
                    ok.effective_max_payload as usize,
                )
                .expect("client should send one associated datagram");

                let echoed = recv_h3_associated_udp_datagram(
                    &mut datagram_reader,
                    control_stream_id,
                    ok.effective_max_payload as usize,
                )
                .await
                .expect("client should receive the echoed associated datagram");
                assert_eq!(echoed.flow_id, udp_open.flow_id);
                assert_eq!(echoed.payload, b"verta-udp-echo");

                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowClose(UdpFlowClose {
                        flow_id: udp_open.flow_id,
                        code: ProtocolErrorCode::NoError,
                        message: "done".to_owned(),
                    }),
                    "udp-flow-close",
                )
                .await;
                control_stream
                    .finish()
                    .await
                    .expect("client control request should finish");
            };

            request_future.await;
            drive_task.abort();
        };

        let (_, _) = tokio::join!(server_future, client_future);
        echo_task.abort();
    }))
    .await;
    result.expect("datagram live test should not time out");
    assert_datagram_transport_selected_without_fallback(&logs, "clean datagram shutdown");
}

#[tokio::test]
async fn loopback_udp_stream_fallback_round_trips_when_rollout_disables_datagrams() {
    let (result, logs) = capture_logs_async(timeout(StdDuration::from_secs(10), async {
        let config = transport_config(true, H3DatagramRollout::Disabled);
        let (server_endpoint, cert_der) = make_server_endpoint(&config);
        let server_addr = server_endpoint
            .local_addr()
            .expect("server endpoint should have a local address");
        let client_endpoint = make_client_endpoint(&config, cert_der);
        let server_config = config.clone();
        let client_config = config.clone();
        let (echo_addr, echo_task) = start_udp_echo_server().await;
        let client_hello =
            Frame::ClientHello(sample_client_hello(mint_token(OffsetDateTime::now_utc())));
        let udp_open = localhost_target(echo_addr.port());

        let server_future = async move {
            let gate = GatewayPreAuthGate::new(GatewayPreAuthBudgets::default())
                .expect("default gateway pre-auth budgets should be valid");
            let connecting = server_endpoint
                .accept()
                .await
                .expect("server should accept one connection");
            let connection = connecting
                .await
                .expect("server-side quic connection should establish");
            let mut builder = server::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(true);
            let mut incoming = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("server h3 connection should initialize");
            let resolver = incoming
                .accept()
                .await
                .expect("server should accept a control request")
                .expect("server should receive one control request");
            let (_request, mut control_stream) = resolver
                .resolve_request()
                .await
                .expect("control request should resolve");

            let permit = gate
                .try_begin_hello()
                .expect("control request should fit within pending-hello budgets");
            let hello = match recv_server_frame(&mut control_stream, "control hello").await {
                Frame::ClientHello(hello) => hello,
                other => panic!("expected client hello on control stream, got {other:?}"),
            };
            permit
                .enforce_control_body_size(
                    ns_carrier_h3::encode_tunnel_frame(&Frame::ClientHello(hello.clone()))
                        .expect("hello should re-encode")
                        .len(),
                )
                .expect("hello body should stay within pre-auth limits");
            permit
                .enforce_handshake_deadline()
                .expect("hello should arrive before the handshake deadline");

            let mut outcome = admit_client_hello(
                &fixture_token_verifier(),
                &hello,
                SessionMode::Tcp,
                server_config.advertised_datagram_mode(true),
            )
            .expect("gateway admission should succeed");

            control_stream
                .send_response(
                    Response::builder()
                        .status(StatusCode::OK)
                        .body(())
                        .expect("control response should build"),
                )
                .await
                .expect("control response should send");
            send_server_frame(
                &mut control_stream,
                &Frame::ServerHello(outcome.response.clone()),
                "server hello",
            )
            .await;

            let open = match recv_server_frame(&mut control_stream, "udp-flow-open").await {
                Frame::UdpFlowOpen(open) => open,
                other => panic!("expected udp-flow-open on control stream, got {other:?}"),
            };
            let ok =
                select_h3_udp_flow_for_config(&mut outcome.controller, &open, &server_config, true)
                    .expect("gateway should select fallback mode");
            assert_eq!(ok.transport_mode, TransportMode::StreamFallback);
            send_server_frame(&mut control_stream, &Frame::UdpFlowOk(ok), "udp-flow-ok").await;

            let fallback = incoming
                .accept()
                .await
                .expect("server should accept one fallback request")
                .expect("server should receive one fallback request");
            let (_request, mut fallback_stream) = fallback
                .resolve_request()
                .await
                .expect("fallback request should resolve");
            let stream_open = match recv_server_frame(&mut fallback_stream, "udp-stream-open").await
            {
                Frame::UdpStreamOpen(open) => open,
                other => panic!("expected udp-stream-open on fallback stream, got {other:?}"),
            };
            assert_eq!(stream_open.flow_id, open.flow_id);

            fallback_stream
                .send_response(
                    Response::builder()
                        .status(StatusCode::OK)
                        .body(())
                        .expect("fallback response should build"),
                )
                .await
                .expect("fallback response should send");
            send_server_frame(
                &mut fallback_stream,
                &Frame::UdpStreamAccept(ns_wire::UdpStreamAccept {
                    flow_id: open.flow_id,
                    metadata: Vec::new(),
                }),
                "udp-stream-accept",
            )
            .await;

            let packet = match recv_server_frame(&mut fallback_stream, "udp-stream-packet").await {
                Frame::UdpStreamPacket(packet) => packet,
                other => panic!("expected udp-stream-packet on fallback stream, got {other:?}"),
            };

            let upstream = UdpSocket::bind(SocketAddr::from((Ipv4Addr::LOCALHOST, 0)))
                .await
                .expect("gateway UDP socket should bind");
            upstream
                .send_to(
                    packet.payload.as_slice(),
                    udp_socket_addr(&open.target, open.target_port),
                )
                .await
                .expect("gateway should send one UDP packet upstream");
            let mut buffer = [0_u8; 1500];
            let (read, _peer) = timeout(StdDuration::from_secs(2), upstream.recv_from(&mut buffer))
                .await
                .expect("gateway should receive an echoed UDP packet before timing out")
                .expect("gateway UDP recv should succeed");

            send_server_frame(
                &mut fallback_stream,
                &Frame::UdpStreamPacket(UdpStreamPacket {
                    payload: buffer[..read].to_vec(),
                }),
                "udp-stream-packet-echo",
            )
            .await;

            let close = match recv_server_frame(&mut fallback_stream, "udp-stream-close").await {
                Frame::UdpStreamClose(close) => close,
                other => panic!("expected udp-stream-close on fallback stream, got {other:?}"),
            };
            assert_eq!(close.flow_id, open.flow_id);
            assert_eq!(close.code, ProtocolErrorCode::NoError);
            fallback_stream
                .finish()
                .await
                .expect("fallback response should finish cleanly");

            let flow_close = match recv_server_frame(&mut control_stream, "udp-flow-close").await {
                Frame::UdpFlowClose(close) => close,
                other => panic!("expected udp-flow-close on control stream, got {other:?}"),
            };
            assert_eq!(flow_close.flow_id, open.flow_id);
            assert_eq!(flow_close.code, ProtocolErrorCode::NoError);
            assert!(outcome.controller.release_udp_flow(open.flow_id));
            finish_or_allow_h3_no_error(
                control_stream.finish().await,
                "control response should finish cleanly",
            );
            let _ = timeout(StdDuration::from_millis(500), server_endpoint.wait_idle()).await;
        };

        let client_future = async move {
            let connection = client_endpoint
                .connect(server_addr, "localhost")
                .expect("client connect should start")
                .await
                .expect("client quic connection should establish");
            let mut builder = client::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(client_config.datagram_runtime_enabled());
            let (mut driver, mut sender) = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("client h3 connection should initialize");
            let mut control_stream = sender
                .send_request(
                    client_config
                        .request_template(H3RequestKind::Control)
                        .expect("control request template should build")
                        .build_request()
                        .expect("control request should build"),
                )
                .await
                .expect("client should open the control request stream");
            let drive_task = tokio::spawn(async move {
                let _ = poll_fn(|cx| driver.poll_close(cx)).await;
            });

            let request_future = async move {
                send_client_frame(&mut control_stream, &client_hello, "client hello").await;
                let response = control_stream
                    .recv_response()
                    .await
                    .expect("control response headers should arrive");
                assert_eq!(response.status(), StatusCode::OK);
                let server_hello =
                    match recv_client_frame(&mut control_stream, "server hello").await {
                        Frame::ServerHello(hello) => hello,
                        other => panic!("expected server hello on control stream, got {other:?}"),
                    };
                assert_eq!(server_hello.datagram_mode, DatagramMode::DisabledByPolicy);

                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowOpen(udp_open.clone()),
                    "udp-flow-open",
                )
                .await;
                let ok = match recv_client_frame(&mut control_stream, "udp-flow-ok").await {
                    Frame::UdpFlowOk(ok) => ok,
                    other => panic!("expected udp-flow-ok on control stream, got {other:?}"),
                };
                assert_eq!(ok.transport_mode, TransportMode::StreamFallback);

                let mut fallback_stream = sender
                    .send_request(
                        client_config
                            .request_template(H3RequestKind::Relay)
                            .expect("fallback request template should build")
                            .build_request()
                            .expect("fallback request should build"),
                    )
                    .await
                    .expect("client should open one UDP fallback request stream");
                send_client_frame(
                    &mut fallback_stream,
                    &Frame::UdpStreamOpen(UdpStreamOpen {
                        flow_id: udp_open.flow_id,
                        metadata: Vec::new(),
                    }),
                    "udp-stream-open",
                )
                .await;
                let fallback_response = fallback_stream
                    .recv_response()
                    .await
                    .expect("fallback response headers should arrive");
                assert_eq!(fallback_response.status(), StatusCode::OK);
                match recv_client_frame(&mut fallback_stream, "udp-stream-accept").await {
                    Frame::UdpStreamAccept(accept) => assert_eq!(accept.flow_id, udp_open.flow_id),
                    other => panic!("expected udp-stream-accept on fallback stream, got {other:?}"),
                }

                send_client_frame(
                    &mut fallback_stream,
                    &Frame::UdpStreamPacket(UdpStreamPacket {
                        payload: b"verta-udp-fallback".to_vec(),
                    }),
                    "udp-stream-packet",
                )
                .await;
                match recv_client_frame(&mut fallback_stream, "udp-stream-packet-echo").await {
                    Frame::UdpStreamPacket(packet) => {
                        assert_eq!(packet.payload, b"verta-udp-fallback")
                    }
                    other => panic!("expected udp-stream-packet echo, got {other:?}"),
                }

                send_client_frame(
                    &mut fallback_stream,
                    &Frame::UdpStreamClose(UdpStreamClose {
                        flow_id: udp_open.flow_id,
                        code: ProtocolErrorCode::NoError,
                        message: "done".to_owned(),
                    }),
                    "udp-stream-close",
                )
                .await;
                fallback_stream
                    .finish()
                    .await
                    .expect("fallback request should finish");

                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowClose(UdpFlowClose {
                        flow_id: udp_open.flow_id,
                        code: ProtocolErrorCode::NoError,
                        message: "done".to_owned(),
                    }),
                    "udp-flow-close",
                )
                .await;
                control_stream
                    .finish()
                    .await
                    .expect("client control request should finish");
            };

            request_future.await;
            drive_task.abort();
        };

        let (_, _) = tokio::join!(server_future, client_future);
        echo_task.abort();
    }))
    .await;
    result.expect("udp fallback live test should not time out");

    assert!(logs.contains("\"event_name\":\"verta.carrier.datagram.selection\""));
    assert!(logs.contains("\"selection\":\"stream_fallback\""));
    assert!(logs.contains("\"datagram_mode\":\"disabled_by_policy\""));
    assert!(logs.contains("\"carrier_available\":true"));
    assert!(logs.contains("\"fallback_allowed\":true"));
    assert!(logs.contains("\"rollout_stage\":\"disabled\""));
}

#[tokio::test]
async fn loopback_udp_stream_fallback_round_trips_when_carrier_support_is_unavailable() {
    let (result, logs) = capture_logs_async(timeout(StdDuration::from_secs(10), async {
        let config = transport_config(true, H3DatagramRollout::Automatic);
        let (server_endpoint, cert_der) = make_server_endpoint(&config);
        let server_addr = server_endpoint
            .local_addr()
            .expect("server endpoint should have a local address");
        let client_endpoint = make_client_endpoint(&config, cert_der);
        let server_config = config.clone();
        let client_config = config.clone();
        let (echo_addr, echo_task) = start_udp_echo_server().await;
        let client_hello =
            Frame::ClientHello(sample_client_hello(mint_token(OffsetDateTime::now_utc())));
        let udp_open = localhost_target(echo_addr.port());

        let server_future = async move {
            let gate = GatewayPreAuthGate::new(GatewayPreAuthBudgets::default())
                .expect("default gateway pre-auth budgets should be valid");
            let connecting = server_endpoint
                .accept()
                .await
                .expect("server should accept one connection");
            let connection = connecting
                .await
                .expect("server-side quic connection should establish");
            let mut builder = server::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(true);
            let mut incoming = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("server h3 connection should initialize");
            let resolver = incoming
                .accept()
                .await
                .expect("server should accept a control request")
                .expect("server should receive one control request");
            let (_request, mut control_stream) = resolver
                .resolve_request()
                .await
                .expect("control request should resolve");

            let permit = gate
                .try_begin_hello()
                .expect("control request should fit within pending-hello budgets");
            let hello = match recv_server_frame(&mut control_stream, "control hello").await {
                Frame::ClientHello(hello) => hello,
                other => panic!("expected client hello on control stream, got {other:?}"),
            };
            permit
                .enforce_control_body_size(
                    ns_carrier_h3::encode_tunnel_frame(&Frame::ClientHello(hello.clone()))
                        .expect("hello should re-encode")
                        .len(),
                )
                .expect("hello body should stay within pre-auth limits");
            permit
                .enforce_handshake_deadline()
                .expect("hello should arrive before the handshake deadline");

            let mut outcome = admit_client_hello(
                &fixture_token_verifier(),
                &hello,
                SessionMode::Tcp,
                server_config.advertised_datagram_mode(false),
            )
            .expect("gateway admission should succeed");

            control_stream
                .send_response(
                    Response::builder()
                        .status(StatusCode::OK)
                        .body(())
                        .expect("control response should build"),
                )
                .await
                .expect("control response should send");
            send_server_frame(
                &mut control_stream,
                &Frame::ServerHello(outcome.response.clone()),
                "server hello",
            )
            .await;

            let open = match recv_server_frame(&mut control_stream, "udp-flow-open").await {
                Frame::UdpFlowOpen(open) => open,
                other => panic!("expected udp-flow-open on control stream, got {other:?}"),
            };
            let ok = select_h3_udp_flow_for_config(
                &mut outcome.controller,
                &open,
                &server_config,
                false,
            )
            .expect("gateway should select fallback mode when carrier datagrams are unavailable");
            assert_eq!(ok.transport_mode, TransportMode::StreamFallback);
            send_server_frame(&mut control_stream, &Frame::UdpFlowOk(ok), "udp-flow-ok").await;

            let fallback = timeout(StdDuration::from_secs(2), incoming.accept())
                .await
                .expect("server should receive the fallback request before timing out")
                .expect("server fallback accept should complete")
                .expect("server should receive one fallback request");
            let (_request, mut fallback_stream) = fallback
                .resolve_request()
                .await
                .expect("fallback request should resolve");
            let stream_open = match timeout(
                StdDuration::from_secs(2),
                recv_server_frame(&mut fallback_stream, "udp-stream-open"),
            )
            .await
            .expect("server should receive udp-stream-open before timing out")
            {
                Frame::UdpStreamOpen(open) => open,
                other => panic!("expected udp-stream-open on fallback stream, got {other:?}"),
            };
            assert_eq!(stream_open.flow_id, open.flow_id);

            fallback_stream
                .send_response(
                    Response::builder()
                        .status(StatusCode::OK)
                        .body(())
                        .expect("fallback response should build"),
                )
                .await
                .expect("fallback response should send");
            send_server_frame(
                &mut fallback_stream,
                &Frame::UdpStreamAccept(ns_wire::UdpStreamAccept {
                    flow_id: open.flow_id,
                    metadata: Vec::new(),
                }),
                "udp-stream-accept",
            )
            .await;

            let packet = match timeout(
                StdDuration::from_secs(2),
                recv_server_frame(&mut fallback_stream, "udp-stream-packet"),
            )
            .await
            .expect("server should receive udp-stream-packet before timing out")
            {
                Frame::UdpStreamPacket(packet) => packet,
                other => panic!("expected udp-stream-packet on fallback stream, got {other:?}"),
            };

            let upstream = UdpSocket::bind(SocketAddr::from((Ipv4Addr::LOCALHOST, 0)))
                .await
                .expect("gateway UDP socket should bind");
            upstream
                .send_to(
                    packet.payload.as_slice(),
                    udp_socket_addr(&open.target, open.target_port),
                )
                .await
                .expect("gateway should send one UDP packet upstream");
            let mut buffer = [0_u8; 1500];
            let (read, _peer) = timeout(StdDuration::from_secs(2), upstream.recv_from(&mut buffer))
                .await
                .expect("gateway should receive an echoed UDP packet before timing out")
                .expect("gateway UDP recv should succeed");

            send_server_frame(
                &mut fallback_stream,
                &Frame::UdpStreamPacket(UdpStreamPacket {
                    payload: buffer[..read].to_vec(),
                }),
                "udp-stream-packet-echo",
            )
            .await;

            let close = match timeout(
                StdDuration::from_secs(2),
                recv_server_frame(&mut fallback_stream, "udp-stream-close"),
            )
            .await
            .expect("server should receive udp-stream-close before timing out")
            {
                Frame::UdpStreamClose(close) => close,
                other => panic!("expected udp-stream-close on fallback stream, got {other:?}"),
            };
            assert_eq!(close.flow_id, open.flow_id);
            assert_eq!(close.code, ProtocolErrorCode::NoError);
            fallback_stream
                .finish()
                .await
                .expect("fallback response should finish cleanly");

            let flow_close = match recv_server_frame(&mut control_stream, "udp-flow-close").await {
                Frame::UdpFlowClose(close) => close,
                other => panic!("expected udp-flow-close on control stream, got {other:?}"),
            };
            assert_eq!(flow_close.flow_id, open.flow_id);
            assert_eq!(flow_close.code, ProtocolErrorCode::NoError);
            assert!(outcome.controller.release_udp_flow(open.flow_id));
            finish_or_allow_h3_no_error(
                control_stream.finish().await,
                "control response should finish cleanly",
            );
            server_endpoint.wait_idle().await;
        };

        let client_future = async move {
            let connection = client_endpoint
                .connect(server_addr, "localhost")
                .expect("client connect should start")
                .await
                .expect("client quic connection should establish");
            let mut builder = client::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(client_config.datagram_runtime_enabled());
            let (mut driver, mut sender) = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("client h3 connection should initialize");
            let mut control_stream = sender
                .send_request(
                    client_config
                        .request_template(H3RequestKind::Control)
                        .expect("control request template should build")
                        .build_request()
                        .expect("control request should build"),
                )
                .await
                .expect("client should open the control request stream");
            let drive_task = tokio::spawn(async move {
                let _ = poll_fn(|cx| driver.poll_close(cx)).await;
            });

            let request_future = async move {
                send_client_frame(&mut control_stream, &client_hello, "client hello").await;
                let response = control_stream
                    .recv_response()
                    .await
                    .expect("control response headers should arrive");
                assert_eq!(response.status(), StatusCode::OK);
                match recv_client_frame(&mut control_stream, "server hello").await {
                    Frame::ServerHello(hello) => {
                        assert_eq!(hello.datagram_mode, DatagramMode::Unavailable)
                    }
                    other => panic!("expected server hello on control stream, got {other:?}"),
                }

                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowOpen(udp_open.clone()),
                    "udp-flow-open",
                )
                .await;
                let ok = match recv_client_frame(&mut control_stream, "udp-flow-ok").await {
                    Frame::UdpFlowOk(ok) => ok,
                    other => panic!("expected udp-flow-ok on control stream, got {other:?}"),
                };
                assert_eq!(ok.transport_mode, TransportMode::StreamFallback);

                let mut fallback_stream = timeout(
                    StdDuration::from_secs(2),
                    sender.send_request(
                        client_config
                            .request_template(H3RequestKind::Relay)
                            .expect("relay request template should build")
                            .build_request()
                            .expect("relay request should build"),
                    ),
                )
                .await
                .expect("client should open the fallback request stream before timing out")
                .expect("client should open one fallback request stream");
                send_client_frame(
                    &mut fallback_stream,
                    &Frame::UdpStreamOpen(UdpStreamOpen {
                        flow_id: udp_open.flow_id,
                        metadata: Vec::new(),
                    }),
                    "udp-stream-open",
                )
                .await;
                let response = timeout(StdDuration::from_secs(2), fallback_stream.recv_response())
                    .await
                    .expect("fallback response headers should arrive before timing out")
                    .expect("fallback response headers should arrive");
                assert_eq!(response.status(), StatusCode::OK);
                match recv_client_frame(&mut fallback_stream, "udp-stream-accept").await {
                    Frame::UdpStreamAccept(accept) => assert_eq!(accept.flow_id, udp_open.flow_id),
                    other => panic!("expected udp-stream-accept, got {other:?}"),
                }

                send_client_frame(
                    &mut fallback_stream,
                    &Frame::UdpStreamPacket(UdpStreamPacket {
                        payload: b"verta-udp-fallback".to_vec(),
                    }),
                    "udp-stream-packet",
                )
                .await;
                match recv_client_frame(&mut fallback_stream, "udp-stream-packet-echo").await {
                    Frame::UdpStreamPacket(packet) => {
                        assert_eq!(packet.payload, b"verta-udp-fallback")
                    }
                    other => panic!("expected udp-stream-packet echo, got {other:?}"),
                }

                send_client_frame(
                    &mut fallback_stream,
                    &Frame::UdpStreamClose(UdpStreamClose {
                        flow_id: udp_open.flow_id,
                        code: ProtocolErrorCode::NoError,
                        message: "done".to_owned(),
                    }),
                    "udp-stream-close",
                )
                .await;
                fallback_stream
                    .finish()
                    .await
                    .expect("fallback request should finish");

                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowClose(UdpFlowClose {
                        flow_id: udp_open.flow_id,
                        code: ProtocolErrorCode::NoError,
                        message: "done".to_owned(),
                    }),
                    "udp-flow-close",
                )
                .await;
                control_stream
                    .finish()
                    .await
                    .expect("client control request should finish");
            };

            request_future.await;
            drive_task.abort();
        };

        let (_, _) = tokio::join!(server_future, client_future);
        echo_task.abort();
    }))
    .await;
    result.expect("carrier-unavailable fallback live test should not time out");

    assert!(logs.contains("\"event_name\":\"verta.carrier.datagram.selection\""));
    assert!(logs.contains("\"selection\":\"stream_fallback\""));
    assert!(logs.contains("\"datagram_mode\":\"unavailable\""));
    assert!(logs.contains("\"carrier_available\":false"));
    assert!(logs.contains("\"fallback_allowed\":true"));
    assert!(logs.contains("\"rollout_stage\":\"automatic\""));
}

#[tokio::test]
async fn loopback_udp_flow_rejects_datagram_only_requests_when_datagrams_are_unavailable() {
    timeout(StdDuration::from_secs(10), async {
        let config = transport_config(true, H3DatagramRollout::Automatic);
        let (server_endpoint, cert_der) = make_server_endpoint(&config);
        let server_addr = server_endpoint
            .local_addr()
            .expect("server endpoint should have a local address");
        let client_endpoint = make_client_endpoint(&config, cert_der);
        let server_config = config.clone();
        let client_hello =
            Frame::ClientHello(sample_client_hello(mint_token(OffsetDateTime::now_utc())));
        let udp_open = datagram_only_target(53);

        let server_future = async move {
            let gate = GatewayPreAuthGate::new(GatewayPreAuthBudgets::default())
                .expect("default gateway pre-auth budgets should be valid");
            let connecting = server_endpoint
                .accept()
                .await
                .expect("server should accept one connection");
            let connection = connecting
                .await
                .expect("server-side quic connection should establish");
            let mut builder = server::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(false);
            let mut incoming = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("server h3 connection should initialize");
            let resolver = incoming
                .accept()
                .await
                .expect("server should accept a control request")
                .expect("server should receive one control request");
            let (_request, mut control_stream) = resolver
                .resolve_request()
                .await
                .expect("control request should resolve");

            let permit = gate
                .try_begin_hello()
                .expect("control request should fit within pending-hello budgets");
            let hello = match recv_server_frame(&mut control_stream, "control hello").await {
                Frame::ClientHello(hello) => hello,
                other => panic!("expected client hello on control stream, got {other:?}"),
            };
            permit
                .enforce_control_body_size(
                    ns_carrier_h3::encode_tunnel_frame(&Frame::ClientHello(hello.clone()))
                        .expect("hello should re-encode")
                        .len(),
                )
                .expect("hello body should stay within pre-auth limits");
            permit
                .enforce_handshake_deadline()
                .expect("hello should arrive before the handshake deadline");

            let mut outcome = admit_client_hello(
                &fixture_token_verifier(),
                &hello,
                SessionMode::Tcp,
                server_config.advertised_datagram_mode(false),
            )
            .expect("gateway admission should succeed");

            control_stream
                .send_response(
                    Response::builder()
                        .status(StatusCode::OK)
                        .body(())
                        .expect("control response should build"),
                )
                .await
                .expect("control response should send");
            send_server_frame(
                &mut control_stream,
                &Frame::ServerHello(outcome.response.clone()),
                "server hello",
            )
            .await;

            let open = match recv_server_frame(&mut control_stream, "udp-flow-open").await {
                Frame::UdpFlowOpen(open) => open,
                other => panic!("expected udp-flow-open on control stream, got {other:?}"),
            };
            let error = select_h3_udp_flow_for_config(
                &mut outcome.controller,
                &open,
                &server_config,
                false,
            )
            .expect_err("datagram-only flow should be rejected");
            send_server_frame(
                &mut control_stream,
                &Frame::UdpFlowClose(UdpFlowClose {
                    flow_id: open.flow_id,
                    code: error
                        .protocol_error_code()
                        .expect("datagram unavailability should map to a protocol code"),
                    message: error.to_string(),
                }),
                "udp-flow-close",
            )
            .await;
            finish_or_allow_h3_no_error(
                control_stream.finish().await,
                "control response should finish cleanly",
            );
            server_endpoint.wait_idle().await;
        };

        let client_future = async move {
            let connection = client_endpoint
                .connect(server_addr, "localhost")
                .expect("client connect should start")
                .await
                .expect("client quic connection should establish");
            let mut builder = client::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(false);
            let (mut driver, mut sender) = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("client h3 connection should initialize");
            let mut control_stream = sender
                .send_request(
                    config
                        .request_template(H3RequestKind::Control)
                        .expect("control request template should build")
                        .build_request()
                        .expect("control request should build"),
                )
                .await
                .expect("client should open the control request stream");
            let drive_task = tokio::spawn(async move {
                let _ = poll_fn(|cx| driver.poll_close(cx)).await;
            });

            let request_future = async move {
                send_client_frame(&mut control_stream, &client_hello, "client hello").await;
                let response = control_stream
                    .recv_response()
                    .await
                    .expect("control response headers should arrive");
                assert_eq!(response.status(), StatusCode::OK);
                let server_hello =
                    match recv_client_frame(&mut control_stream, "server hello").await {
                        Frame::ServerHello(hello) => hello,
                        other => panic!("expected server hello on control stream, got {other:?}"),
                    };
                assert_eq!(server_hello.datagram_mode, DatagramMode::Unavailable);

                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowOpen(udp_open.clone()),
                    "udp-flow-open",
                )
                .await;
                match recv_client_frame(&mut control_stream, "udp-flow-close").await {
                    Frame::UdpFlowClose(close) => {
                        assert_eq!(close.flow_id, udp_open.flow_id);
                        assert_eq!(close.code, ProtocolErrorCode::UdpDatagramUnavailable);
                    }
                    other => panic!("expected udp-flow-close rejection, got {other:?}"),
                }
                control_stream
                    .finish()
                    .await
                    .expect("client control request should finish");
            };

            request_future.await;
            drive_task.abort();
        };

        let (_, _) = tokio::join!(server_future, client_future);
    })
    .await
    .expect("udp rejection live test should not time out");
}

#[tokio::test]
async fn loopback_h3_datagrams_continue_after_repeated_bounded_loss() {
    let (result, logs) = capture_logs_async(timeout(StdDuration::from_secs(10), async {
        let config = transport_config(true, H3DatagramRollout::Automatic);
        let (server_endpoint, cert_der) = make_server_endpoint(&config);
        let server_addr = server_endpoint
            .local_addr()
            .expect("server endpoint should have a local address");
        let client_endpoint = make_client_endpoint(&config, cert_der);
        let server_config = config.clone();
        let client_config = config.clone();
        let client_hello =
            Frame::ClientHello(sample_client_hello(mint_token(OffsetDateTime::now_utc())));
        let udp_open = localhost_target(53);

        let server_future = async move {
            let gate = GatewayPreAuthGate::new(GatewayPreAuthBudgets::default())
                .expect("default gateway pre-auth budgets should be valid");
            let connecting = server_endpoint
                .accept()
                .await
                .expect("server should accept one connection");
            let connection = connecting
                .await
                .expect("server-side quic connection should establish");
            let mut builder = server::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(true);
            let mut incoming = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("server h3 connection should initialize");
            let mut datagram_reader = incoming.get_datagram_reader();
            let resolver = incoming
                .accept()
                .await
                .expect("server should accept a control request")
                .expect("server should receive one control request");
            let (_request, mut control_stream) = resolver
                .resolve_request()
                .await
                .expect("control request should resolve");
            let control_stream_id = control_stream.send_id();

            let permit = gate
                .try_begin_hello()
                .expect("control request should fit within pending-hello budgets");
            let hello = match recv_server_frame(&mut control_stream, "control hello").await {
                Frame::ClientHello(hello) => hello,
                other => panic!("expected client hello on control stream, got {other:?}"),
            };
            permit
                .enforce_control_body_size(
                    ns_carrier_h3::encode_tunnel_frame(&Frame::ClientHello(hello.clone()))
                        .expect("hello should re-encode")
                        .len(),
                )
                .expect("hello body should stay within pre-auth limits");
            permit
                .enforce_handshake_deadline()
                .expect("hello should arrive before the handshake deadline");

            let mut outcome = admit_client_hello(
                &fixture_token_verifier(),
                &hello,
                SessionMode::Tcp,
                server_config.advertised_datagram_mode(true),
            )
            .expect("gateway admission should succeed");

            control_stream
                .send_response(
                    Response::builder()
                        .status(StatusCode::OK)
                        .body(())
                        .expect("control response should build"),
                )
                .await
                .expect("control response should send");
            send_server_frame(
                &mut control_stream,
                &Frame::ServerHello(outcome.response.clone()),
                "server hello",
            )
            .await;

            let open = match recv_server_frame(&mut control_stream, "udp-flow-open").await {
                Frame::UdpFlowOpen(open) => open,
                other => panic!("expected udp-flow-open on control stream, got {other:?}"),
            };
            let ok =
                select_h3_udp_flow_for_config(&mut outcome.controller, &open, &server_config, true)
                    .expect("gateway should select datagram mode");
            send_server_frame(
                &mut control_stream,
                &Frame::UdpFlowOk(ok.clone()),
                "udp-flow-ok",
            )
            .await;

            let first = recv_h3_associated_udp_datagram(
                &mut datagram_reader,
                control_stream_id,
                ok.effective_max_payload as usize,
            )
            .await
            .expect("gateway should receive the first datagram");
            assert_eq!(first.payload, b"lost-one");

            let second = recv_h3_associated_udp_datagram(
                &mut datagram_reader,
                control_stream_id,
                ok.effective_max_payload as usize,
            )
            .await
            .expect("gateway should receive the second datagram");
            assert_eq!(second.payload, b"lost-two");

            let third = recv_h3_associated_udp_datagram(
                &mut datagram_reader,
                control_stream_id,
                ok.effective_max_payload as usize,
            )
            .await
            .expect("gateway should receive the third datagram");
            assert_eq!(third.payload, b"survivor");

            let mut datagram_sender = incoming.get_datagram_sender(control_stream_id);
            send_h3_associated_udp_datagram(
                &mut datagram_sender,
                &UdpDatagram {
                    flow_id: third.flow_id,
                    flags: DatagramFlags::new(0).expect("fixture datagram flags should be valid"),
                    payload: third.payload.clone(),
                },
                ok.effective_max_payload as usize,
            )
            .expect("gateway should echo the third datagram only");

            let close = match recv_server_frame(&mut control_stream, "udp-flow-close").await {
                Frame::UdpFlowClose(close) => close,
                other => panic!("expected udp-flow-close on control stream, got {other:?}"),
            };
            assert_eq!(close.flow_id, open.flow_id);
            assert_eq!(close.code, ProtocolErrorCode::NoError);
            let fallback_accept = timeout(StdDuration::from_millis(250), incoming.accept()).await;
            assert!(
                !matches!(fallback_accept, Ok(Ok(Some(_)))),
                "clean shutdown after prolonged impairment must not silently open a fallback stream"
            );
            assert!(outcome.controller.release_udp_flow(open.flow_id));
            finish_or_allow_h3_no_error(
                control_stream.finish().await,
                "control response should finish cleanly",
            );
            server_endpoint.wait_idle().await;
        };

        let client_future = async move {
            let connection = client_endpoint
                .connect(server_addr, "localhost")
                .expect("client connect should start")
                .await
                .expect("client quic connection should establish");
            let mut builder = client::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(client_config.datagram_runtime_enabled());
            let (mut driver, mut sender) = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("client h3 connection should initialize");
            let mut control_stream = sender
                .send_request(
                    client_config
                        .request_template(H3RequestKind::Control)
                        .expect("control request template should build")
                        .build_request()
                        .expect("control request should build"),
                )
                .await
                .expect("client should open the control request stream");
            let control_stream_id = control_stream.id();
            let mut datagram_reader = driver.get_datagram_reader();
            let mut datagram_sender = driver.get_datagram_sender(control_stream_id);
            let drive_task = tokio::spawn(async move {
                let _ = poll_fn(|cx| driver.poll_close(cx)).await;
            });

            let request_future = async move {
                send_client_frame(&mut control_stream, &client_hello, "client hello").await;
                let response = control_stream
                    .recv_response()
                    .await
                    .expect("control response headers should arrive");
                assert_eq!(response.status(), StatusCode::OK);
                match recv_client_frame(&mut control_stream, "server hello").await {
                    Frame::ServerHello(hello) => {
                        assert_eq!(hello.datagram_mode, DatagramMode::AvailableAndEnabled)
                    }
                    other => panic!("expected server hello on control stream, got {other:?}"),
                }

                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowOpen(udp_open.clone()),
                    "udp-flow-open",
                )
                .await;
                let ok = match recv_client_frame(&mut control_stream, "udp-flow-ok").await {
                    Frame::UdpFlowOk(ok) => ok,
                    other => panic!("expected udp-flow-ok on control stream, got {other:?}"),
                };

                send_h3_associated_udp_datagram(
                    &mut datagram_sender,
                    &UdpDatagram {
                        flow_id: udp_open.flow_id,
                        flags: DatagramFlags::new(0)
                            .expect("fixture datagram flags should be valid"),
                        payload: b"lost-one".to_vec(),
                    },
                    ok.effective_max_payload as usize,
                )
                .expect("client should send the first datagram");
                let loss = timeout(
                    StdDuration::from_millis(250),
                    recv_h3_associated_udp_datagram(
                        &mut datagram_reader,
                        control_stream_id,
                        ok.effective_max_payload as usize,
                    ),
                )
                .await;
                assert!(
                    loss.is_err(),
                    "the first intentionally dropped datagram should time out"
                );

                send_h3_associated_udp_datagram(
                    &mut datagram_sender,
                    &UdpDatagram {
                        flow_id: udp_open.flow_id,
                        flags: DatagramFlags::new(0)
                            .expect("fixture datagram flags should be valid"),
                        payload: b"lost-two".to_vec(),
                    },
                    ok.effective_max_payload as usize,
                )
                .expect("client should send a second datagram after bounded loss");
                let second_loss = timeout(
                    StdDuration::from_millis(250),
                    recv_h3_associated_udp_datagram(
                        &mut datagram_reader,
                        control_stream_id,
                        ok.effective_max_payload as usize,
                    ),
                )
                .await;
                assert!(
                    second_loss.is_err(),
                    "the second intentionally dropped datagram should time out"
                );

                send_h3_associated_udp_datagram(
                    &mut datagram_sender,
                    &UdpDatagram {
                        flow_id: udp_open.flow_id,
                        flags: DatagramFlags::new(0)
                            .expect("fixture datagram flags should be valid"),
                        payload: b"survivor".to_vec(),
                    },
                    ok.effective_max_payload as usize,
                )
                .expect("client should send a third datagram after repeated bounded loss");
                let echoed = recv_h3_associated_udp_datagram(
                    &mut datagram_reader,
                    control_stream_id,
                    ok.effective_max_payload as usize,
                )
                .await
                .expect("client should still receive the third echoed datagram");
                assert_eq!(echoed.payload, b"survivor");

                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowClose(UdpFlowClose {
                        flow_id: udp_open.flow_id,
                        code: ProtocolErrorCode::NoError,
                        message: "done".to_owned(),
                    }),
                    "udp-flow-close",
                )
                .await;
                control_stream
                    .finish()
                    .await
                    .expect("client control request should finish");
            };

            request_future.await;
            drive_task.abort();
        };

        let (_, _) = tokio::join!(server_future, client_future);
    }))
    .await;
    result.expect("repeated bounded-loss datagram live test should not time out");
    assert_datagram_lab_profile_keeps_selected_transport(&logs, UdpWanLabProfileId::LossBurst);
    assert!(logs.contains("\"rollout_stage\":\"automatic\""));
}

#[tokio::test]
async fn loopback_h3_datagrams_tolerate_bounded_reordering_without_fallback() {
    let (result, logs) = capture_logs_async(timeout(StdDuration::from_secs(10), async {
        let config = transport_config(true, H3DatagramRollout::Automatic);
        let (server_endpoint, cert_der) = make_server_endpoint(&config);
        let server_addr = server_endpoint
            .local_addr()
            .expect("server endpoint should have a local address");
        let client_endpoint = make_client_endpoint(&config, cert_der);
        let server_config = config.clone();
        let client_config = config.clone();
        let client_hello =
            Frame::ClientHello(sample_client_hello(mint_token(OffsetDateTime::now_utc())));
        let udp_open = localhost_target(53);

        let server_future = async move {
            let gate = GatewayPreAuthGate::new(GatewayPreAuthBudgets::default())
                .expect("default gateway pre-auth budgets should be valid");
            let connecting = server_endpoint
                .accept()
                .await
                .expect("server should accept one connection");
            let connection = connecting
                .await
                .expect("server-side quic connection should establish");
            let mut builder = server::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(true);
            let mut incoming = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("server h3 connection should initialize");
            let mut datagram_reader = incoming.get_datagram_reader();
            let resolver = incoming
                .accept()
                .await
                .expect("server should accept a control request")
                .expect("server should receive one control request");
            let (_request, mut control_stream) = resolver
                .resolve_request()
                .await
                .expect("control request should resolve");
            let control_stream_id = control_stream.send_id();

            let permit = gate
                .try_begin_hello()
                .expect("control request should fit within pending-hello budgets");
            let hello = match recv_server_frame(&mut control_stream, "control hello").await {
                Frame::ClientHello(hello) => hello,
                other => panic!("expected client hello on control stream, got {other:?}"),
            };
            permit
                .enforce_control_body_size(
                    ns_carrier_h3::encode_tunnel_frame(&Frame::ClientHello(hello.clone()))
                        .expect("hello should re-encode")
                        .len(),
                )
                .expect("hello body should stay within pre-auth limits");
            permit
                .enforce_handshake_deadline()
                .expect("hello should arrive before the handshake deadline");

            let mut outcome = admit_client_hello(
                &fixture_token_verifier(),
                &hello,
                SessionMode::Tcp,
                server_config.advertised_datagram_mode(true),
            )
            .expect("gateway admission should succeed");

            control_stream
                .send_response(
                    Response::builder()
                        .status(StatusCode::OK)
                        .body(())
                        .expect("control response should build"),
                )
                .await
                .expect("control response should send");
            send_server_frame(
                &mut control_stream,
                &Frame::ServerHello(outcome.response.clone()),
                "server hello",
            )
            .await;

            let open = match recv_server_frame(&mut control_stream, "udp-flow-open").await {
                Frame::UdpFlowOpen(open) => open,
                other => panic!("expected udp-flow-open on control stream, got {other:?}"),
            };
            let ok =
                select_h3_udp_flow_for_config(&mut outcome.controller, &open, &server_config, true)
                    .expect("gateway should select datagram mode");
            send_server_frame(
                &mut control_stream,
                &Frame::UdpFlowOk(ok.clone()),
                "udp-flow-ok",
            )
            .await;

            let first = recv_h3_associated_udp_datagram(
                &mut datagram_reader,
                control_stream_id,
                ok.effective_max_payload as usize,
            )
            .await
            .expect("gateway should receive the first datagram");
            let second = recv_h3_associated_udp_datagram(
                &mut datagram_reader,
                control_stream_id,
                ok.effective_max_payload as usize,
            )
            .await
            .expect("gateway should receive the second datagram");
            assert_eq!(first.payload, b"first");
            assert_eq!(second.payload, b"second");

            let mut datagram_sender = incoming.get_datagram_sender(control_stream_id);
            send_h3_associated_udp_datagram(
                &mut datagram_sender,
                &UdpDatagram {
                    flow_id: open.flow_id,
                    flags: DatagramFlags::new(0).expect("fixture datagram flags should be valid"),
                    payload: second.payload.clone(),
                },
                ok.effective_max_payload as usize,
            )
            .expect("gateway should echo the second datagram first");
            send_h3_associated_udp_datagram(
                &mut datagram_sender,
                &UdpDatagram {
                    flow_id: open.flow_id,
                    flags: DatagramFlags::new(0).expect("fixture datagram flags should be valid"),
                    payload: first.payload.clone(),
                },
                ok.effective_max_payload as usize,
            )
            .expect("gateway should echo the first datagram second");

            let close = match recv_server_frame(&mut control_stream, "udp-flow-close").await {
                Frame::UdpFlowClose(close) => close,
                other => panic!("expected udp-flow-close on control stream, got {other:?}"),
            };
            assert_eq!(close.flow_id, open.flow_id);
            assert_eq!(close.code, ProtocolErrorCode::NoError);
            assert!(outcome.controller.release_udp_flow(open.flow_id));
            finish_or_allow_h3_no_error(
                control_stream.finish().await,
                "control response should finish cleanly",
            );
            server_endpoint.wait_idle().await;
        };

        let client_future = async move {
            let connection = client_endpoint
                .connect(server_addr, "localhost")
                .expect("client connect should start")
                .await
                .expect("client quic connection should establish");
            let mut builder = client::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(client_config.datagram_runtime_enabled());
            let (mut driver, mut sender) = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("client h3 connection should initialize");
            let mut control_stream = sender
                .send_request(
                    client_config
                        .request_template(H3RequestKind::Control)
                        .expect("control request template should build")
                        .build_request()
                        .expect("control request should build"),
                )
                .await
                .expect("client should open the control request stream");
            let control_stream_id = control_stream.id();
            let mut datagram_reader = driver.get_datagram_reader();
            let mut datagram_sender = driver.get_datagram_sender(control_stream_id);
            let drive_task = tokio::spawn(async move {
                let _ = poll_fn(|cx| driver.poll_close(cx)).await;
            });

            let request_future = async move {
                send_client_frame(&mut control_stream, &client_hello, "client hello").await;
                let response = control_stream
                    .recv_response()
                    .await
                    .expect("control response headers should arrive");
                assert_eq!(response.status(), StatusCode::OK);
                match recv_client_frame(&mut control_stream, "server hello").await {
                    Frame::ServerHello(hello) => {
                        assert_eq!(hello.datagram_mode, DatagramMode::AvailableAndEnabled)
                    }
                    other => panic!("expected server hello on control stream, got {other:?}"),
                }

                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowOpen(udp_open.clone()),
                    "udp-flow-open",
                )
                .await;
                let ok = match recv_client_frame(&mut control_stream, "udp-flow-ok").await {
                    Frame::UdpFlowOk(ok) => ok,
                    other => panic!("expected udp-flow-ok on control stream, got {other:?}"),
                };

                for payload in [b"first".as_slice(), b"second".as_slice()] {
                    send_h3_associated_udp_datagram(
                        &mut datagram_sender,
                        &UdpDatagram {
                            flow_id: udp_open.flow_id,
                            flags: DatagramFlags::new(0)
                                .expect("fixture datagram flags should be valid"),
                            payload: payload.to_vec(),
                        },
                        ok.effective_max_payload as usize,
                    )
                    .expect("client should send datagrams before reordering");
                }

                let first_echo = recv_h3_associated_udp_datagram(
                    &mut datagram_reader,
                    control_stream_id,
                    ok.effective_max_payload as usize,
                )
                .await
                .expect("client should receive the first reordered datagram");
                let second_echo = recv_h3_associated_udp_datagram(
                    &mut datagram_reader,
                    control_stream_id,
                    ok.effective_max_payload as usize,
                )
                .await
                .expect("client should receive the second reordered datagram");
                assert_eq!(first_echo.payload, b"second");
                assert_eq!(second_echo.payload, b"first");

                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowClose(UdpFlowClose {
                        flow_id: udp_open.flow_id,
                        code: ProtocolErrorCode::NoError,
                        message: "done".to_owned(),
                    }),
                    "udp-flow-close",
                )
                .await;
                control_stream
                    .finish()
                    .await
                    .expect("client control request should finish");
            };

            request_future.await;
            drive_task.abort();
        };

        let (_, _) = tokio::join!(server_future, client_future);
    }))
    .await;
    result.expect("reordering datagram live test should not time out");
    assert_datagram_lab_profile_keeps_selected_transport(&logs, UdpWanLabProfileId::ReorderWindow);
    assert!(logs.contains("\"rollout_stage\":\"automatic\""));
}

#[tokio::test]
async fn loopback_h3_datagrams_tolerate_delayed_delivery_and_short_black_hole_without_fallback() {
    let (result, logs) = capture_logs_async(timeout(StdDuration::from_secs(10), async {
        let config = transport_config(true, H3DatagramRollout::Automatic);
        let (server_endpoint, cert_der) = make_server_endpoint(&config);
        let server_addr = server_endpoint
            .local_addr()
            .expect("server endpoint should have a local address");
        let client_endpoint = make_client_endpoint(&config, cert_der);
        let server_config = config.clone();
        let client_config = config.clone();
        let client_hello =
            Frame::ClientHello(sample_client_hello(mint_token(OffsetDateTime::now_utc())));
        let udp_open = localhost_target(53);

        let server_future = async move {
            let gate = GatewayPreAuthGate::new(GatewayPreAuthBudgets::default())
                .expect("default gateway pre-auth budgets should be valid");
            let connecting = server_endpoint
                .accept()
                .await
                .expect("server should accept one connection");
            let connection = connecting
                .await
                .expect("server-side quic connection should establish");
            let mut builder = server::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(true);
            let mut incoming = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("server h3 connection should initialize");
            let mut datagram_reader = incoming.get_datagram_reader();
            let resolver = incoming
                .accept()
                .await
                .expect("server should accept a control request")
                .expect("server should receive one control request");
            let (_request, mut control_stream) = resolver
                .resolve_request()
                .await
                .expect("control request should resolve");
            let control_stream_id = control_stream.send_id();

            let permit = gate
                .try_begin_hello()
                .expect("control request should fit within pending-hello budgets");
            let hello = match recv_server_frame(&mut control_stream, "control hello").await {
                Frame::ClientHello(hello) => hello,
                other => panic!("expected client hello on control stream, got {other:?}"),
            };
            permit
                .enforce_control_body_size(
                    ns_carrier_h3::encode_tunnel_frame(&Frame::ClientHello(hello.clone()))
                        .expect("hello should re-encode")
                        .len(),
                )
                .expect("hello body should stay within pre-auth limits");
            permit
                .enforce_handshake_deadline()
                .expect("hello should arrive before the handshake deadline");

            let mut outcome = admit_client_hello(
                &fixture_token_verifier(),
                &hello,
                SessionMode::Tcp,
                server_config.advertised_datagram_mode(true),
            )
            .expect("gateway admission should succeed");

            control_stream
                .send_response(
                    Response::builder()
                        .status(StatusCode::OK)
                        .body(())
                        .expect("control response should build"),
                )
                .await
                .expect("control response should send");
            send_server_frame(
                &mut control_stream,
                &Frame::ServerHello(outcome.response.clone()),
                "server hello",
            )
            .await;

            let open = match recv_server_frame(&mut control_stream, "udp-flow-open").await {
                Frame::UdpFlowOpen(open) => open,
                other => panic!("expected udp-flow-open on control stream, got {other:?}"),
            };
            let ok =
                select_h3_udp_flow_for_config(&mut outcome.controller, &open, &server_config, true)
                    .expect("gateway should select datagram mode");
            send_server_frame(
                &mut control_stream,
                &Frame::UdpFlowOk(ok.clone()),
                "udp-flow-ok",
            )
            .await;

            let mut datagram_sender = incoming.get_datagram_sender(control_stream_id);

            let delayed = recv_h3_associated_udp_datagram(
                &mut datagram_reader,
                control_stream_id,
                ok.effective_max_payload as usize,
            )
            .await
            .expect("gateway should receive the delayed datagram");
            assert_eq!(delayed.payload, b"slow-path");
            tokio::time::sleep(StdDuration::from_millis(200)).await;
            send_h3_associated_udp_datagram(
                &mut datagram_sender,
                &UdpDatagram {
                    flow_id: open.flow_id,
                    flags: DatagramFlags::new(0).expect("fixture datagram flags should be valid"),
                    payload: delayed.payload.clone(),
                },
                ok.effective_max_payload as usize,
            )
            .expect("gateway should echo the delayed datagram");

            let dropped = recv_h3_associated_udp_datagram(
                &mut datagram_reader,
                control_stream_id,
                ok.effective_max_payload as usize,
            )
            .await
            .expect("gateway should receive the black-holed datagram");
            assert_eq!(dropped.payload, b"black-hole");
            let fallback_accept = timeout(StdDuration::from_millis(250), incoming.accept()).await;
            assert!(
                !matches!(fallback_accept, Ok(Ok(Some(_)))),
                "the client must not silently open a fallback stream after datagram degradation"
            );

            let recovered = recv_h3_associated_udp_datagram(
                &mut datagram_reader,
                control_stream_id,
                ok.effective_max_payload as usize,
            )
            .await
            .expect("gateway should receive a recovery datagram after the short black hole");
            assert_eq!(recovered.payload, b"recover");
            send_h3_associated_udp_datagram(
                &mut datagram_sender,
                &UdpDatagram {
                    flow_id: open.flow_id,
                    flags: DatagramFlags::new(0).expect("fixture datagram flags should be valid"),
                    payload: recovered.payload.clone(),
                },
                ok.effective_max_payload as usize,
            )
            .expect("gateway should echo the recovery datagram");

            let dropped_again = recv_h3_associated_udp_datagram(
                &mut datagram_reader,
                control_stream_id,
                ok.effective_max_payload as usize,
            )
            .await
            .expect("gateway should receive the repeated black-holed datagram");
            assert_eq!(dropped_again.payload, b"black-hole-2");
            let fallback_accept = timeout(StdDuration::from_millis(250), incoming.accept()).await;
            assert!(
                !matches!(fallback_accept, Ok(Ok(Some(_)))),
                "the client must not silently open a fallback stream during prolonged datagram degradation"
            );

            let recovered_again = recv_h3_associated_udp_datagram(
                &mut datagram_reader,
                control_stream_id,
                ok.effective_max_payload as usize,
            )
            .await
            .expect("gateway should receive the second recovery datagram");
            assert_eq!(recovered_again.payload, b"recover-2");
            send_h3_associated_udp_datagram(
                &mut datagram_sender,
                &UdpDatagram {
                    flow_id: open.flow_id,
                    flags: DatagramFlags::new(0).expect("fixture datagram flags should be valid"),
                    payload: recovered_again.payload.clone(),
                },
                ok.effective_max_payload as usize,
            )
            .expect("gateway should echo the second recovery datagram");

            let dropped_third = recv_h3_associated_udp_datagram(
                &mut datagram_reader,
                control_stream_id,
                ok.effective_max_payload as usize,
            )
            .await
            .expect("gateway should receive the prolonged black-holed datagram");
            assert_eq!(dropped_third.payload, b"black-hole-3");
            let fallback_accept = timeout(StdDuration::from_millis(250), incoming.accept()).await;
            assert!(
                !matches!(fallback_accept, Ok(Ok(Some(_)))),
                "the client must not silently open a fallback stream during prolonged repeated datagram degradation"
            );

            let recovered_third = recv_h3_associated_udp_datagram(
                &mut datagram_reader,
                control_stream_id,
                ok.effective_max_payload as usize,
            )
            .await
            .expect("gateway should receive the third recovery datagram");
            assert_eq!(recovered_third.payload, b"recover-3");
            send_h3_associated_udp_datagram(
                &mut datagram_sender,
                &UdpDatagram {
                    flow_id: open.flow_id,
                    flags: DatagramFlags::new(0).expect("fixture datagram flags should be valid"),
                    payload: recovered_third.payload.clone(),
                },
                ok.effective_max_payload as usize,
            )
            .expect("gateway should echo the third recovery datagram");

            let close = match recv_server_frame(&mut control_stream, "udp-flow-close").await {
                Frame::UdpFlowClose(close) => close,
                other => panic!("expected udp-flow-close on control stream, got {other:?}"),
            };
            assert_eq!(close.flow_id, open.flow_id);
            assert_eq!(close.code, ProtocolErrorCode::NoError);
            assert!(outcome.controller.release_udp_flow(open.flow_id));
            finish_or_allow_h3_no_error(
                control_stream.finish().await,
                "control response should finish cleanly",
            );
            server_endpoint.wait_idle().await;
        };

        let client_future = async move {
            let connection = client_endpoint
                .connect(server_addr, "localhost")
                .expect("client connect should start")
                .await
                .expect("client quic connection should establish");
            let mut builder = client::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(client_config.datagram_runtime_enabled());
            let (mut driver, mut sender) = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("client h3 connection should initialize");
            let mut control_stream = sender
                .send_request(
                    client_config
                        .request_template(H3RequestKind::Control)
                        .expect("control request template should build")
                        .build_request()
                        .expect("control request should build"),
                )
                .await
                .expect("client should open the control request stream");
            let control_stream_id = control_stream.id();
            let mut datagram_reader = driver.get_datagram_reader();
            let mut datagram_sender = driver.get_datagram_sender(control_stream_id);
            let mut drive_task = tokio::spawn(async move {
                let _ = poll_fn(|cx| driver.poll_close(cx)).await;
            });

            let request_future = async move {
                send_client_frame(&mut control_stream, &client_hello, "client hello").await;
                let response = control_stream
                    .recv_response()
                    .await
                    .expect("control response headers should arrive");
                assert_eq!(response.status(), StatusCode::OK);
                match recv_client_frame(&mut control_stream, "server hello").await {
                    Frame::ServerHello(hello) => {
                        assert_eq!(hello.datagram_mode, DatagramMode::AvailableAndEnabled)
                    }
                    other => panic!("expected server hello on control stream, got {other:?}"),
                }

                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowOpen(udp_open.clone()),
                    "udp-flow-open",
                )
                .await;
                let ok = match recv_client_frame(&mut control_stream, "udp-flow-ok").await {
                    Frame::UdpFlowOk(ok) => ok,
                    other => panic!("expected udp-flow-ok on control stream, got {other:?}"),
                };

                send_h3_associated_udp_datagram(
                    &mut datagram_sender,
                    &UdpDatagram {
                        flow_id: udp_open.flow_id,
                        flags: DatagramFlags::new(0)
                            .expect("fixture datagram flags should be valid"),
                        payload: b"slow-path".to_vec(),
                    },
                    ok.effective_max_payload as usize,
                )
                .expect("client should send the delayed datagram");
                let delayed_echo = timeout(
                    StdDuration::from_millis(900),
                    recv_h3_associated_udp_datagram(
                        &mut datagram_reader,
                        control_stream_id,
                        ok.effective_max_payload as usize,
                    ),
                )
                .await
                .expect("delayed echo should arrive before the test timeout")
                .expect("delayed echo should decode");
                assert_eq!(delayed_echo.payload, b"slow-path");

                send_h3_associated_udp_datagram(
                    &mut datagram_sender,
                    &UdpDatagram {
                        flow_id: udp_open.flow_id,
                        flags: DatagramFlags::new(0)
                            .expect("fixture datagram flags should be valid"),
                        payload: b"black-hole".to_vec(),
                    },
                    ok.effective_max_payload as usize,
                )
                .expect("client should send the black-holed datagram");
                assert!(
                    timeout(
                        StdDuration::from_millis(350),
                        recv_h3_associated_udp_datagram(
                            &mut datagram_reader,
                            control_stream_id,
                            ok.effective_max_payload as usize,
                        ),
                    )
                    .await
                    .is_err(),
                    "the short datagram black hole should not produce a fallback or echoed datagram"
                );

                send_h3_associated_udp_datagram(
                    &mut datagram_sender,
                    &UdpDatagram {
                        flow_id: udp_open.flow_id,
                        flags: DatagramFlags::new(0)
                            .expect("fixture datagram flags should be valid"),
                        payload: b"recover".to_vec(),
                    },
                    ok.effective_max_payload as usize,
                )
                .expect("client should send a recovery datagram after the short black hole");
                let recovery_echo = recv_h3_associated_udp_datagram(
                    &mut datagram_reader,
                    control_stream_id,
                    ok.effective_max_payload as usize,
                )
                .await
                .expect("recovery echo should still arrive over datagrams");
                assert_eq!(recovery_echo.payload, b"recover");

                send_h3_associated_udp_datagram(
                    &mut datagram_sender,
                    &UdpDatagram {
                        flow_id: udp_open.flow_id,
                        flags: DatagramFlags::new(0)
                            .expect("fixture datagram flags should be valid"),
                        payload: b"black-hole-2".to_vec(),
                    },
                    ok.effective_max_payload as usize,
                )
                .expect("client should send the repeated black-holed datagram");
                assert!(
                    timeout(
                        StdDuration::from_millis(350),
                        recv_h3_associated_udp_datagram(
                            &mut datagram_reader,
                            control_stream_id,
                            ok.effective_max_payload as usize,
                        ),
                    )
                    .await
                    .is_err(),
                    "repeated datagram degradation must stay fail closed without fallback"
                );

                send_h3_associated_udp_datagram(
                    &mut datagram_sender,
                    &UdpDatagram {
                        flow_id: udp_open.flow_id,
                        flags: DatagramFlags::new(0)
                            .expect("fixture datagram flags should be valid"),
                        payload: b"recover-2".to_vec(),
                    },
                    ok.effective_max_payload as usize,
                )
                .expect("client should send the second recovery datagram");
                let second_recovery_echo = recv_h3_associated_udp_datagram(
                    &mut datagram_reader,
                    control_stream_id,
                    ok.effective_max_payload as usize,
                )
                .await
                .expect("the second recovery echo should still arrive over datagrams");
                assert_eq!(second_recovery_echo.payload, b"recover-2");

                send_h3_associated_udp_datagram(
                    &mut datagram_sender,
                    &UdpDatagram {
                        flow_id: udp_open.flow_id,
                        flags: DatagramFlags::new(0)
                            .expect("fixture datagram flags should be valid"),
                        payload: b"black-hole-3".to_vec(),
                    },
                    ok.effective_max_payload as usize,
                )
                .expect("client should send the prolonged black-holed datagram");
                assert!(
                    timeout(
                        StdDuration::from_millis(350),
                        recv_h3_associated_udp_datagram(
                            &mut datagram_reader,
                            control_stream_id,
                            ok.effective_max_payload as usize,
                        ),
                    )
                    .await
                    .is_err(),
                    "prolonged repeated datagram degradation must stay fail closed without fallback"
                );

                send_h3_associated_udp_datagram(
                    &mut datagram_sender,
                    &UdpDatagram {
                        flow_id: udp_open.flow_id,
                        flags: DatagramFlags::new(0)
                            .expect("fixture datagram flags should be valid"),
                        payload: b"recover-3".to_vec(),
                    },
                    ok.effective_max_payload as usize,
                )
                .expect("client should send the third recovery datagram");
                let third_recovery_echo = recv_h3_associated_udp_datagram(
                    &mut datagram_reader,
                    control_stream_id,
                    ok.effective_max_payload as usize,
                )
                .await
                .expect("the third recovery echo should still arrive over datagrams");
                assert_eq!(third_recovery_echo.payload, b"recover-3");

                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowClose(UdpFlowClose {
                        flow_id: udp_open.flow_id,
                        code: ProtocolErrorCode::NoError,
                        message: "done".to_owned(),
                    }),
                    "udp-flow-close",
                )
                .await;
                control_stream
                    .finish()
                    .await
                    .expect("client control request should finish");
                let _ = timeout(StdDuration::from_millis(500), control_stream.recv_data()).await;
            };

            request_future.await;
            drop(sender);
            settle_h3_driver_or_abort(&mut drive_task).await;
        };

        let (_, _) = tokio::join!(server_future, client_future);
    }))
    .await;
    result.expect("delayed-delivery datagram live test should not time out");

    assert_datagram_lab_profile_keeps_selected_transport(
        &logs,
        UdpWanLabProfileId::DelayedDeliveryShortBlackHole,
    );
    assert!(logs.contains("\"rollout_stage\":\"automatic\""));
}

#[tokio::test]
async fn loopback_h3_datagrams_continue_after_mixed_delay_and_loss_without_fallback() {
    let (result, logs) = capture_logs_async(timeout(StdDuration::from_secs(15), async {
        let config = transport_config(true, H3DatagramRollout::Automatic);
        let (server_endpoint, cert_der) = make_server_endpoint(&config);
        let server_addr = server_endpoint
            .local_addr()
            .expect("server endpoint should have a local address");
        let client_endpoint = make_client_endpoint(&config, cert_der);
        let server_config = config.clone();
        let client_config = config.clone();
        let client_hello =
            Frame::ClientHello(sample_client_hello(mint_token(OffsetDateTime::now_utc())));
        let udp_open = localhost_target(53);

        let server_future = async move {
            let gate = GatewayPreAuthGate::new(GatewayPreAuthBudgets::default())
                .expect("default gateway pre-auth budgets should be valid");
            let connecting = server_endpoint
                .accept()
                .await
                .expect("server should accept one connection");
            let connection = connecting
                .await
                .expect("server-side quic connection should establish");
            let mut builder = server::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(true);
            let mut incoming = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("server h3 connection should initialize");
            let mut datagram_reader = incoming.get_datagram_reader();
            let resolver = incoming
                .accept()
                .await
                .expect("server should accept a control request")
                .expect("server should receive one control request");
            let (_request, mut control_stream) = resolver
                .resolve_request()
                .await
                .expect("control request should resolve");
            let control_stream_id = control_stream.send_id();

            let permit = gate
                .try_begin_hello()
                .expect("control request should fit within pending-hello budgets");
            let hello = match recv_server_frame(&mut control_stream, "control hello").await {
                Frame::ClientHello(hello) => hello,
                other => panic!("expected client hello on control stream, got {other:?}"),
            };
            permit
                .enforce_control_body_size(
                    ns_carrier_h3::encode_tunnel_frame(&Frame::ClientHello(hello.clone()))
                        .expect("hello should re-encode")
                        .len(),
                )
                .expect("hello body should stay within pre-auth limits");
            permit
                .enforce_handshake_deadline()
                .expect("hello should arrive before the handshake deadline");

            let mut outcome = admit_client_hello(
                &fixture_token_verifier(),
                &hello,
                SessionMode::Tcp,
                server_config.advertised_datagram_mode(true),
            )
            .expect("gateway admission should succeed");

            control_stream
                .send_response(
                    Response::builder()
                        .status(StatusCode::OK)
                        .body(())
                        .expect("control response should build"),
                )
                .await
                .expect("control response should send");
            send_server_frame(
                &mut control_stream,
                &Frame::ServerHello(outcome.response.clone()),
                "server hello",
            )
            .await;

            let open = match recv_server_frame(&mut control_stream, "udp-flow-open").await {
                Frame::UdpFlowOpen(open) => open,
                other => panic!("expected udp-flow-open on control stream, got {other:?}"),
            };
            let ok =
                select_h3_udp_flow_for_config(&mut outcome.controller, &open, &server_config, true)
                    .expect("gateway should select datagram mode");
            send_server_frame(
                &mut control_stream,
                &Frame::UdpFlowOk(ok.clone()),
                "udp-flow-ok",
            )
            .await;

            let mut datagram_sender = incoming.get_datagram_sender(control_stream_id);
            let mut echoed_probe_payloads = BTreeSet::new();
            loop {
                let datagram = match timeout(
                    StdDuration::from_millis(900),
                    recv_h3_associated_udp_datagram(
                        &mut datagram_reader,
                        control_stream_id,
                        ok.effective_max_payload as usize,
                    ),
                )
                .await
                {
                    Ok(Ok(datagram)) => datagram,
                    Ok(Err(_)) if !echoed_probe_payloads.is_empty() => break,
                    Ok(Err(error)) => {
                        panic!("gateway should decode mixed-loss probe datagrams: {error}")
                    }
                    Err(_) if !echoed_probe_payloads.is_empty() => break,
                    Err(_) => panic!(
                        "gateway should receive at least one mixed-loss probe datagram before idle timeout"
                    ),
                };
                assert!(
                    datagram.payload.starts_with(b"probe-"),
                    "mixed-loss profile should only exchange probe payloads, got {:?}",
                    datagram.payload
                );
                echoed_probe_payloads.insert(datagram.payload.clone());
                send_h3_associated_udp_datagram(
                    &mut datagram_sender,
                    &UdpDatagram {
                        flow_id: open.flow_id,
                        flags: DatagramFlags::new(0)
                            .expect("fixture datagram flags should be valid"),
                        payload: datagram.payload.clone(),
                    },
                    ok.effective_max_payload as usize,
                )
                .expect("gateway should echo mixed-loss probe datagrams");
            }

            let fallback_accept = timeout(StdDuration::from_millis(250), incoming.accept()).await;
            assert!(
                !matches!(fallback_accept, Ok(Ok(Some(_)))),
                "mixed delay/loss must not silently open a fallback stream"
            );

            let close = match recv_server_frame(&mut control_stream, "udp-flow-close").await {
                Frame::UdpFlowClose(close) => close,
                other => panic!("expected udp-flow-close on control stream, got {other:?}"),
            };
            assert_eq!(close.flow_id, open.flow_id);
            assert_eq!(close.code, ProtocolErrorCode::NoError);
            assert!(outcome.controller.release_udp_flow(open.flow_id));
            finish_or_allow_h3_no_error(
                control_stream.finish().await,
                "control response should finish cleanly",
            );
            server_endpoint.wait_idle().await;
        };

        let client_future = async move {
            let connection = client_endpoint
                .connect(server_addr, "localhost")
                .expect("client connect should start")
                .await
                .expect("client quic connection should establish");
            let mut builder = client::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(client_config.datagram_runtime_enabled());
            let (mut driver, mut sender) = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("client h3 connection should initialize");
            let mut control_stream = sender
                .send_request(
                    client_config
                        .request_template(H3RequestKind::Control)
                        .expect("control request template should build")
                        .build_request()
                        .expect("control request should build"),
                )
                .await
                .expect("client should open the control request stream");
            let control_stream_id = control_stream.id();
            let mut datagram_reader = driver.get_datagram_reader();
            let mut datagram_sender = driver.get_datagram_sender(control_stream_id);
            let mut drive_task = tokio::spawn(async move {
                let _ = poll_fn(|cx| driver.poll_close(cx)).await;
            });

            let request_future = async move {
                send_client_frame(&mut control_stream, &client_hello, "client hello").await;
                let response = control_stream
                    .recv_response()
                    .await
                    .expect("control response headers should arrive");
                assert_eq!(response.status(), StatusCode::OK);
                match recv_client_frame(&mut control_stream, "server hello").await {
                    Frame::ServerHello(hello) => {
                        assert_eq!(hello.datagram_mode, DatagramMode::AvailableAndEnabled)
                    }
                    other => panic!("expected server hello on control stream, got {other:?}"),
                }

                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowOpen(udp_open.clone()),
                    "udp-flow-open",
                )
                .await;
                let ok = match recv_client_frame(&mut control_stream, "udp-flow-ok").await {
                    Frame::UdpFlowOk(ok) => ok,
                    other => panic!("expected udp-flow-ok on control stream, got {other:?}"),
                };

                let mut echoed_probe_payloads = BTreeSet::new();
                for sequence in 1..=12 {
                    send_h3_associated_udp_datagram(
                        &mut datagram_sender,
                        &UdpDatagram {
                            flow_id: udp_open.flow_id,
                            flags: DatagramFlags::new(0)
                                .expect("fixture datagram flags should be valid"),
                            payload: format!("probe-{sequence}").into_bytes(),
                        },
                        ok.effective_max_payload as usize,
                    )
                    .expect("client should send mixed-loss probe datagrams");

                    let echoed = timeout(
                        StdDuration::from_millis(700),
                        recv_h3_associated_udp_datagram(
                            &mut datagram_reader,
                            control_stream_id,
                            ok.effective_max_payload as usize,
                        ),
                    )
                    .await;
                    let Ok(echoed) = echoed else {
                        continue;
                    };
                    let echoed = echoed.expect("mixed-loss probe echo should decode");
                    assert!(
                        echoed.payload.starts_with(b"probe-"),
                        "mixed-loss profile should only echo probe payloads, got {:?}",
                        echoed.payload
                    );
                    echoed_probe_payloads.insert(echoed.payload);
                    break;
                }
                assert!(
                    !echoed_probe_payloads.is_empty(),
                    "mixed-loss probe echo should arrive before retries are exhausted"
                );

                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowClose(UdpFlowClose {
                        flow_id: udp_open.flow_id,
                        code: ProtocolErrorCode::NoError,
                        message: "done".to_owned(),
                    }),
                    "udp-flow-close",
                )
                .await;
                control_stream
                    .finish()
                    .await
                    .expect("client control request should finish");
                let _ = timeout(StdDuration::from_millis(500), control_stream.recv_data()).await;
            };

            request_future.await;
            drop(sender);
            settle_h3_driver_or_abort(&mut drive_task).await;
        };

        let (_, _) = tokio::join!(server_future, client_future);
    }))
    .await;
    result.expect("mixed delay/loss datagram live test should not time out");

    assert_datagram_lab_profile_keeps_selected_transport(
        &logs,
        UdpWanLabProfileId::MixedDelayLossRecovery,
    );
    assert!(logs.contains("\"rollout_stage\":\"automatic\""));
}

#[tokio::test]
async fn loopback_h3_datagrams_accept_payload_at_effective_mtu_ceiling() {
    timeout(StdDuration::from_secs(10), async {
        let config = transport_config(true, H3DatagramRollout::Automatic);
        let (server_endpoint, cert_der) = make_server_endpoint(&config);
        let server_addr = server_endpoint
            .local_addr()
            .expect("server endpoint should have a local address");
        let client_endpoint = make_client_endpoint(&config, cert_der);
        let server_config = config.clone();
        let client_config = config.clone();
        let client_hello =
            Frame::ClientHello(sample_client_hello(mint_token(OffsetDateTime::now_utc())));
        let udp_open = localhost_target(53);

        let server_future = async move {
            let gate = GatewayPreAuthGate::new(GatewayPreAuthBudgets::default())
                .expect("default gateway pre-auth budgets should be valid");
            let connecting = server_endpoint
                .accept()
                .await
                .expect("server should accept one connection");
            let connection = connecting
                .await
                .expect("server-side quic connection should establish");
            let mut builder = server::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(true);
            let mut incoming = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("server h3 connection should initialize");
            let mut datagram_reader = incoming.get_datagram_reader();
            let resolver = incoming
                .accept()
                .await
                .expect("server should accept a control request")
                .expect("server should receive one control request");
            let (_request, mut control_stream) = resolver
                .resolve_request()
                .await
                .expect("control request should resolve");
            let control_stream_id = control_stream.send_id();

            let permit = gate
                .try_begin_hello()
                .expect("control request should fit within pending-hello budgets");
            let hello = match recv_server_frame(&mut control_stream, "control hello").await {
                Frame::ClientHello(hello) => hello,
                other => panic!("expected client hello on control stream, got {other:?}"),
            };
            permit
                .enforce_control_body_size(
                    ns_carrier_h3::encode_tunnel_frame(&Frame::ClientHello(hello.clone()))
                        .expect("hello should re-encode")
                        .len(),
                )
                .expect("hello body should stay within pre-auth limits");
            permit
                .enforce_handshake_deadline()
                .expect("hello should arrive before the handshake deadline");

            let mut outcome = admit_client_hello(
                &fixture_token_verifier(),
                &hello,
                SessionMode::Tcp,
                server_config.advertised_datagram_mode(true),
            )
            .expect("gateway admission should succeed");

            control_stream
                .send_response(
                    Response::builder()
                        .status(StatusCode::OK)
                        .body(())
                        .expect("control response should build"),
                )
                .await
                .expect("control response should send");
            send_server_frame(
                &mut control_stream,
                &Frame::ServerHello(outcome.response.clone()),
                "server hello",
            )
            .await;

            let open = match recv_server_frame(&mut control_stream, "udp-flow-open").await {
                Frame::UdpFlowOpen(open) => open,
                other => panic!("expected udp-flow-open on control stream, got {other:?}"),
            };
            let ok =
                select_h3_udp_flow_for_config(&mut outcome.controller, &open, &server_config, true)
                    .expect("gateway should select datagram mode");
            send_server_frame(
                &mut control_stream,
                &Frame::UdpFlowOk(ok.clone()),
                "udp-flow-ok",
            )
            .await;

            let datagram = recv_h3_associated_udp_datagram(
                &mut datagram_reader,
                control_stream_id,
                ok.effective_max_payload as usize,
            )
            .await
            .expect("gateway should receive one MTU-adjacent datagram");
            assert_eq!(datagram.payload.len(), ok.effective_max_payload as usize);

            let mut datagram_sender = incoming.get_datagram_sender(control_stream_id);
            send_h3_associated_udp_datagram(
                &mut datagram_sender,
                &datagram,
                ok.effective_max_payload as usize,
            )
            .expect("gateway should echo the MTU-adjacent datagram");

            let close = match recv_server_frame(&mut control_stream, "udp-flow-close").await {
                Frame::UdpFlowClose(close) => close,
                other => panic!("expected udp-flow-close on control stream, got {other:?}"),
            };
            assert_eq!(close.flow_id, open.flow_id);
            assert_eq!(close.code, ProtocolErrorCode::NoError);
            assert!(outcome.controller.release_udp_flow(open.flow_id));
            finish_or_allow_h3_no_error(
                control_stream.finish().await,
                "control response should finish cleanly",
            );
            server_endpoint.wait_idle().await;
        };

        let client_future = async move {
            let connection = client_endpoint
                .connect(server_addr, "localhost")
                .expect("client connect should start")
                .await
                .expect("client quic connection should establish");
            let mut builder = client::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(client_config.datagram_runtime_enabled());
            let (mut driver, mut sender) = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("client h3 connection should initialize");
            let mut control_stream = sender
                .send_request(
                    client_config
                        .request_template(H3RequestKind::Control)
                        .expect("control request template should build")
                        .build_request()
                        .expect("control request should build"),
                )
                .await
                .expect("client should open the control request stream");
            let control_stream_id = control_stream.id();
            let mut datagram_reader = driver.get_datagram_reader();
            let mut datagram_sender = driver.get_datagram_sender(control_stream_id);
            let drive_task = tokio::spawn(async move {
                let _ = poll_fn(|cx| driver.poll_close(cx)).await;
            });

            let request_future = async move {
                send_client_frame(&mut control_stream, &client_hello, "client hello").await;
                let response = control_stream
                    .recv_response()
                    .await
                    .expect("control response headers should arrive");
                assert_eq!(response.status(), StatusCode::OK);
                match recv_client_frame(&mut control_stream, "server hello").await {
                    Frame::ServerHello(hello) => {
                        assert_eq!(hello.datagram_mode, DatagramMode::AvailableAndEnabled)
                    }
                    other => panic!("expected server hello on control stream, got {other:?}"),
                }

                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowOpen(udp_open.clone()),
                    "udp-flow-open",
                )
                .await;
                let ok = match recv_client_frame(&mut control_stream, "udp-flow-ok").await {
                    Frame::UdpFlowOk(ok) => ok,
                    other => panic!("expected udp-flow-ok on control stream, got {other:?}"),
                };

                let payload = vec![0x5a; ok.effective_max_payload as usize];
                send_h3_associated_udp_datagram(
                    &mut datagram_sender,
                    &UdpDatagram {
                        flow_id: udp_open.flow_id,
                        flags: DatagramFlags::new(0)
                            .expect("fixture datagram flags should be valid"),
                        payload: payload.clone(),
                    },
                    ok.effective_max_payload as usize,
                )
                .expect("client should send a payload exactly at the effective MTU ceiling");

                let echoed = recv_h3_associated_udp_datagram(
                    &mut datagram_reader,
                    control_stream_id,
                    ok.effective_max_payload as usize,
                )
                .await
                .expect("client should receive the echoed MTU-adjacent datagram");
                assert_eq!(echoed.payload, payload);

                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowClose(UdpFlowClose {
                        flow_id: udp_open.flow_id,
                        code: ProtocolErrorCode::NoError,
                        message: "done".to_owned(),
                    }),
                    "udp-flow-close",
                )
                .await;
                control_stream
                    .finish()
                    .await
                    .expect("client control request should finish");
            };

            request_future.await;
            drive_task.abort();
        };

        let (_, _) = tokio::join!(server_future, client_future);
    })
    .await
    .expect("MTU-adjacent datagram live test should not time out");
}

#[tokio::test]
async fn loopback_h3_datagrams_reject_oversized_payloads_and_keep_flow_state() {
    let (result, logs) = capture_logs_async(timeout(StdDuration::from_secs(10), async {
        let config = transport_config(true, H3DatagramRollout::Automatic);
        let (server_endpoint, cert_der) = make_server_endpoint(&config);
        let server_addr = server_endpoint
            .local_addr()
            .expect("server endpoint should have a local address");
        let client_endpoint = make_client_endpoint(&config, cert_der);
        let server_config = config.clone();
        let client_config = config.clone();
        let client_hello =
            Frame::ClientHello(sample_client_hello(mint_token(OffsetDateTime::now_utc())));
        let udp_open = localhost_target(53);

        let server_future = async move {
            let gate = GatewayPreAuthGate::new(GatewayPreAuthBudgets::default())
                .expect("default gateway pre-auth budgets should be valid");
            let connecting = server_endpoint
                .accept()
                .await
                .expect("server should accept one connection");
            let connection = connecting
                .await
                .expect("server-side quic connection should establish");
            let mut builder = server::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(true);
            let mut incoming = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("server h3 connection should initialize");
            let mut datagram_reader = incoming.get_datagram_reader();
            let resolver = incoming
                .accept()
                .await
                .expect("server should accept a control request")
                .expect("server should receive one control request");
            let (_request, mut control_stream) = resolver
                .resolve_request()
                .await
                .expect("control request should resolve");
            let control_stream_id = control_stream.send_id();

            let permit = gate
                .try_begin_hello()
                .expect("control request should fit within pending-hello budgets");
            let hello = match recv_server_frame(&mut control_stream, "control hello").await {
                Frame::ClientHello(hello) => hello,
                other => panic!("expected client hello on control stream, got {other:?}"),
            };
            permit
                .enforce_control_body_size(
                    ns_carrier_h3::encode_tunnel_frame(&Frame::ClientHello(hello.clone()))
                        .expect("hello should re-encode")
                        .len(),
                )
                .expect("hello body should stay within pre-auth limits");
            permit
                .enforce_handshake_deadline()
                .expect("hello should arrive before the handshake deadline");

            let mut outcome = admit_client_hello(
                &fixture_token_verifier(),
                &hello,
                SessionMode::Tcp,
                server_config.advertised_datagram_mode(true),
            )
            .expect("gateway admission should succeed");

            control_stream
                .send_response(
                    Response::builder()
                        .status(StatusCode::OK)
                        .body(())
                        .expect("control response should build"),
                )
                .await
                .expect("control response should send");
            send_server_frame(
                &mut control_stream,
                &Frame::ServerHello(outcome.response.clone()),
                "server hello",
            )
            .await;

            let open = match recv_server_frame(&mut control_stream, "udp-flow-open").await {
                Frame::UdpFlowOpen(open) => open,
                other => panic!("expected udp-flow-open on control stream, got {other:?}"),
            };
            let ok =
                select_h3_udp_flow_for_config(&mut outcome.controller, &open, &server_config, true)
                    .expect("gateway should select datagram mode");
            send_server_frame(
                &mut control_stream,
                &Frame::UdpFlowOk(ok.clone()),
                "udp-flow-ok",
            )
            .await;

            let datagram = recv_h3_associated_udp_datagram(
                &mut datagram_reader,
                control_stream_id,
                ok.effective_max_payload as usize,
            )
            .await
            .expect("gateway should receive the first valid datagram after the oversize rejection");
            assert_eq!(datagram.payload, b"after-oversize");

            let mut datagram_sender = incoming.get_datagram_sender(control_stream_id);
            send_h3_associated_udp_datagram(
                &mut datagram_sender,
                &UdpDatagram {
                    flow_id: datagram.flow_id,
                    flags: DatagramFlags::new(0).expect("fixture datagram flags should be valid"),
                    payload: datagram.payload.clone(),
                },
                ok.effective_max_payload as usize,
            )
            .expect("gateway should echo the valid datagram");

            let close = match recv_server_frame(&mut control_stream, "udp-flow-close").await {
                Frame::UdpFlowClose(close) => close,
                other => panic!("expected udp-flow-close on control stream, got {other:?}"),
            };
            assert_eq!(close.flow_id, open.flow_id);
            assert!(outcome.controller.release_udp_flow(open.flow_id));
            finish_or_allow_h3_no_error(
                control_stream.finish().await,
                "control response should finish cleanly",
            );
            server_endpoint.wait_idle().await;
        };

        let client_future = async move {
            let connection = client_endpoint
                .connect(server_addr, "localhost")
                .expect("client connect should start")
                .await
                .expect("client quic connection should establish");
            let mut builder = client::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(client_config.datagram_runtime_enabled());
            let (mut driver, mut sender) = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("client h3 connection should initialize");
            let mut control_stream = sender
                .send_request(
                    client_config
                        .request_template(H3RequestKind::Control)
                        .expect("control request template should build")
                        .build_request()
                        .expect("control request should build"),
                )
                .await
                .expect("client should open the control request stream");
            let control_stream_id = control_stream.id();
            let mut datagram_reader = driver.get_datagram_reader();
            let mut datagram_sender = driver.get_datagram_sender(control_stream_id);
            let drive_task = tokio::spawn(async move {
                let _ = poll_fn(|cx| driver.poll_close(cx)).await;
            });

            let request_future = async move {
                send_client_frame(&mut control_stream, &client_hello, "client hello").await;
                let response = control_stream
                    .recv_response()
                    .await
                    .expect("control response headers should arrive");
                assert_eq!(response.status(), StatusCode::OK);
                match recv_client_frame(&mut control_stream, "server hello").await {
                    Frame::ServerHello(hello) => {
                        assert_eq!(hello.datagram_mode, DatagramMode::AvailableAndEnabled)
                    }
                    other => panic!("expected server hello on control stream, got {other:?}"),
                }

                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowOpen(udp_open.clone()),
                    "udp-flow-open",
                )
                .await;
                let ok = match recv_client_frame(&mut control_stream, "udp-flow-ok").await {
                    Frame::UdpFlowOk(ok) => ok,
                    other => panic!("expected udp-flow-ok on control stream, got {other:?}"),
                };

                let oversized = send_h3_associated_udp_datagram(
                    &mut datagram_sender,
                    &UdpDatagram {
                        flow_id: udp_open.flow_id,
                        flags: DatagramFlags::new(0)
                            .expect("fixture datagram flags should be valid"),
                        payload: vec![0_u8; ok.effective_max_payload as usize + 1],
                    },
                    ok.effective_max_payload as usize,
                )
                .expect_err("oversized datagram should be rejected before it is sent");
                assert_eq!(oversized.kind, ns_session::TransportErrorKind::Backpressure);

                send_h3_associated_udp_datagram(
                    &mut datagram_sender,
                    &UdpDatagram {
                        flow_id: udp_open.flow_id,
                        flags: DatagramFlags::new(0)
                            .expect("fixture datagram flags should be valid"),
                        payload: b"after-oversize".to_vec(),
                    },
                    ok.effective_max_payload as usize,
                )
                .expect("valid datagram should still send after the oversize rejection");
                let echoed = recv_h3_associated_udp_datagram(
                    &mut datagram_reader,
                    control_stream_id,
                    ok.effective_max_payload as usize,
                )
                .await
                .expect("client should receive the echoed valid datagram");
                assert_eq!(echoed.payload, b"after-oversize");

                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowClose(UdpFlowClose {
                        flow_id: udp_open.flow_id,
                        code: ProtocolErrorCode::NoError,
                        message: "done".to_owned(),
                    }),
                    "udp-flow-close",
                )
                .await;
                control_stream
                    .finish()
                    .await
                    .expect("client control request should finish");
            };

            request_future.await;
            drive_task.abort();
        };

        let (_, _) = tokio::join!(server_future, client_future);
    }))
    .await;

    result.expect("oversized datagram live test should not time out");
    assert!(logs.contains("\"event_name\":\"verta.carrier.datagram.guard\""));
    assert!(logs.contains("\"reason\":\"udp_payload_too_large\""));
}

#[tokio::test]
async fn loopback_h3_datagrams_reject_wrong_associated_stream_and_recover() {
    let (result, logs) = capture_logs_async(timeout(StdDuration::from_secs(10), async {
        let config = transport_config(true, H3DatagramRollout::Automatic);
        let (server_endpoint, cert_der) = make_server_endpoint(&config);
        let server_addr = server_endpoint
            .local_addr()
            .expect("server endpoint should have a local address");
        let client_endpoint = make_client_endpoint(&config, cert_der);
        let server_config = config.clone();
        let client_config = config.clone();
        let client_hello =
            Frame::ClientHello(sample_client_hello(mint_token(OffsetDateTime::now_utc())));
        let udp_open = localhost_target(53);

        let server_future = async move {
            let gate = GatewayPreAuthGate::new(GatewayPreAuthBudgets::default())
                .expect("default gateway pre-auth budgets should be valid");
            let connecting = server_endpoint
                .accept()
                .await
                .expect("server should accept one connection");
            let connection = connecting
                .await
                .expect("server-side quic connection should establish");
            let mut builder = server::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(true);
            let mut incoming = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("server h3 connection should initialize");
            let resolver = incoming
                .accept()
                .await
                .expect("server should accept a control request")
                .expect("server should receive one control request");
            let (_request, mut control_stream) = resolver
                .resolve_request()
                .await
                .expect("control request should resolve");
            let control_stream_id = control_stream.send_id();

            let permit = gate
                .try_begin_hello()
                .expect("control request should fit within pending-hello budgets");
            let hello = match recv_server_frame(&mut control_stream, "control hello").await {
                Frame::ClientHello(hello) => hello,
                other => panic!("expected client hello on control stream, got {other:?}"),
            };
            permit
                .enforce_control_body_size(
                    ns_carrier_h3::encode_tunnel_frame(&Frame::ClientHello(hello.clone()))
                        .expect("hello should re-encode")
                        .len(),
                )
                .expect("hello body should stay within pre-auth limits");
            permit
                .enforce_handshake_deadline()
                .expect("hello should arrive before the handshake deadline");

            let mut outcome = admit_client_hello(
                &fixture_token_verifier(),
                &hello,
                SessionMode::Tcp,
                server_config.advertised_datagram_mode(true),
            )
            .expect("gateway admission should succeed");

            control_stream
                .send_response(
                    Response::builder()
                        .status(StatusCode::OK)
                        .body(())
                        .expect("control response should build"),
                )
                .await
                .expect("control response should send");
            send_server_frame(
                &mut control_stream,
                &Frame::ServerHello(outcome.response.clone()),
                "server hello",
            )
            .await;

            let open = match recv_server_frame(&mut control_stream, "udp-flow-open").await {
                Frame::UdpFlowOpen(open) => open,
                other => panic!("expected udp-flow-open on control stream, got {other:?}"),
            };
            let ok =
                select_h3_udp_flow_for_config(&mut outcome.controller, &open, &server_config, true)
                    .expect("gateway should select datagram mode");
            send_server_frame(
                &mut control_stream,
                &Frame::UdpFlowOk(ok.clone()),
                "udp-flow-ok",
            )
            .await;

            let fallback = incoming
                .accept()
                .await
                .expect("server should accept one relay request")
                .expect("server should receive one relay request");
            let (_request, mut relay_stream) = fallback
                .resolve_request()
                .await
                .expect("relay request should resolve");
            relay_stream
                .send_response(
                    Response::builder()
                        .status(StatusCode::OK)
                        .body(())
                        .expect("relay response should build"),
                )
                .await
                .expect("relay response should send");

            let mut datagram_sender = incoming.get_datagram_sender(control_stream_id);
            send_h3_associated_udp_datagram(
                &mut datagram_sender,
                &UdpDatagram {
                    flow_id: open.flow_id,
                    flags: DatagramFlags::new(0).expect("fixture datagram flags should be valid"),
                    payload: b"mismatch".to_vec(),
                },
                ok.effective_max_payload as usize,
            )
            .expect("gateway should send the first associated datagram");
            send_h3_associated_udp_datagram(
                &mut datagram_sender,
                &UdpDatagram {
                    flow_id: open.flow_id,
                    flags: DatagramFlags::new(0).expect("fixture datagram flags should be valid"),
                    payload: b"recovered".to_vec(),
                },
                ok.effective_max_payload as usize,
            )
            .expect("gateway should send the second associated datagram");

            relay_stream
                .finish()
                .await
                .expect("relay response should finish cleanly");
            let close = match recv_server_frame(&mut control_stream, "udp-flow-close").await {
                Frame::UdpFlowClose(close) => close,
                other => panic!("expected udp-flow-close on control stream, got {other:?}"),
            };
            assert_eq!(close.flow_id, open.flow_id);
            assert!(outcome.controller.release_udp_flow(open.flow_id));
            finish_or_allow_h3_no_error(
                control_stream.finish().await,
                "control response should finish cleanly",
            );
            server_endpoint.wait_idle().await;
        };

        let client_future = async move {
            let connection = client_endpoint
                .connect(server_addr, "localhost")
                .expect("client connect should start")
                .await
                .expect("client quic connection should establish");
            let mut builder = client::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(client_config.datagram_runtime_enabled());
            let (mut driver, mut sender) = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("client h3 connection should initialize");
            let mut control_stream = sender
                .send_request(
                    client_config
                        .request_template(H3RequestKind::Control)
                        .expect("control request template should build")
                        .build_request()
                        .expect("control request should build"),
                )
                .await
                .expect("client should open the control request stream");
            let control_stream_id = control_stream.id();
            let mut datagram_reader = driver.get_datagram_reader();
            let drive_task = tokio::spawn(async move {
                let _ = poll_fn(|cx| driver.poll_close(cx)).await;
            });

            let request_future = async move {
                send_client_frame(&mut control_stream, &client_hello, "client hello").await;
                let response = control_stream
                    .recv_response()
                    .await
                    .expect("control response headers should arrive");
                assert_eq!(response.status(), StatusCode::OK);
                match recv_client_frame(&mut control_stream, "server hello").await {
                    Frame::ServerHello(hello) => {
                        assert_eq!(hello.datagram_mode, DatagramMode::AvailableAndEnabled)
                    }
                    other => panic!("expected server hello on control stream, got {other:?}"),
                }

                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowOpen(udp_open.clone()),
                    "udp-flow-open",
                )
                .await;
                let ok = match recv_client_frame(&mut control_stream, "udp-flow-ok").await {
                    Frame::UdpFlowOk(ok) => ok,
                    other => panic!("expected udp-flow-ok on control stream, got {other:?}"),
                };

                let mut relay_stream = sender
                    .send_request(
                        client_config
                            .request_template(H3RequestKind::Relay)
                            .expect("relay request template should build")
                            .build_request()
                            .expect("relay request should build"),
                    )
                    .await
                    .expect("client should open one relay request stream");
                let wrong_stream_id = relay_stream.id();
                let relay_response = relay_stream
                    .recv_response()
                    .await
                    .expect("relay response headers should arrive");
                assert_eq!(relay_response.status(), StatusCode::OK);

                let mismatch = recv_h3_associated_udp_datagram(
                    &mut datagram_reader,
                    wrong_stream_id,
                    ok.effective_max_payload as usize,
                )
                .await
                .expect_err("wrong associated stream should be rejected");
                assert_eq!(
                    mismatch.kind,
                    ns_session::TransportErrorKind::ProtocolViolation
                );

                let recovered = recv_h3_associated_udp_datagram(
                    &mut datagram_reader,
                    control_stream_id,
                    ok.effective_max_payload as usize,
                )
                .await
                .expect("correct associated stream should still recover cleanly");
                assert_eq!(recovered.payload, b"recovered");

                relay_stream
                    .finish()
                    .await
                    .expect("relay request should finish cleanly");
                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowClose(UdpFlowClose {
                        flow_id: udp_open.flow_id,
                        code: ProtocolErrorCode::NoError,
                        message: "done".to_owned(),
                    }),
                    "udp-flow-close",
                )
                .await;
                control_stream
                    .finish()
                    .await
                    .expect("client control request should finish");
            };

            request_future.await;
            drive_task.abort();
        };

        let (_, _) = tokio::join!(server_future, client_future);
    }))
    .await;

    result.expect("wrong associated-stream live test should not time out");
    assert_datagram_lab_profile_keeps_selected_transport(
        &logs,
        UdpWanLabProfileId::AssociatedStreamGuardRecovery,
    );
    assert!(logs.contains("\"event_name\":\"verta.carrier.datagram.guard\""));
    assert!(logs.contains("\"reason\":\"udp_associated_stream_mismatch\""));
}

#[tokio::test]
async fn loopback_h3_datagrams_reject_unknown_flows_after_close() {
    let (result, logs) = capture_logs_async(timeout(StdDuration::from_secs(10), async {
        let config = transport_config(true, H3DatagramRollout::Automatic);
        let (server_endpoint, cert_der) = make_server_endpoint(&config);
        let server_addr = server_endpoint
            .local_addr()
            .expect("server endpoint should have a local address");
        let client_endpoint = make_client_endpoint(&config, cert_der);
        let server_config = config.clone();
        let client_config = config.clone();
        let client_hello =
            Frame::ClientHello(sample_client_hello(mint_token(OffsetDateTime::now_utc())));
        let udp_open = localhost_target(53);

        let server_future = async move {
            let gate = GatewayPreAuthGate::new(GatewayPreAuthBudgets::default())
                .expect("default gateway pre-auth budgets should be valid");
            let connecting = server_endpoint
                .accept()
                .await
                .expect("server should accept one connection");
            let connection = connecting
                .await
                .expect("server-side quic connection should establish");
            let mut builder = server::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(true);
            let mut incoming = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("server h3 connection should initialize");
            let mut datagram_reader = incoming.get_datagram_reader();
            let resolver = incoming
                .accept()
                .await
                .expect("server should accept a control request")
                .expect("server should receive one control request");
            let (_request, mut control_stream) = resolver
                .resolve_request()
                .await
                .expect("control request should resolve");
            let control_stream_id = control_stream.send_id();

            let permit = gate
                .try_begin_hello()
                .expect("control request should fit within pending-hello budgets");
            let hello = match recv_server_frame(&mut control_stream, "control hello").await {
                Frame::ClientHello(hello) => hello,
                other => panic!("expected client hello on control stream, got {other:?}"),
            };
            permit
                .enforce_control_body_size(
                    ns_carrier_h3::encode_tunnel_frame(&Frame::ClientHello(hello.clone()))
                        .expect("hello should re-encode")
                        .len(),
                )
                .expect("hello body should stay within pre-auth limits");
            permit
                .enforce_handshake_deadline()
                .expect("hello should arrive before the handshake deadline");

            let mut outcome = admit_client_hello(
                &fixture_token_verifier(),
                &hello,
                SessionMode::Tcp,
                server_config.advertised_datagram_mode(true),
            )
            .expect("gateway admission should succeed");

            control_stream
                .send_response(
                    Response::builder()
                        .status(StatusCode::OK)
                        .body(())
                        .expect("control response should build"),
                )
                .await
                .expect("control response should send");
            send_server_frame(
                &mut control_stream,
                &Frame::ServerHello(outcome.response.clone()),
                "server hello",
            )
            .await;

            let open = match recv_server_frame(&mut control_stream, "udp-flow-open").await {
                Frame::UdpFlowOpen(open) => open,
                other => panic!("expected udp-flow-open on control stream, got {other:?}"),
            };
            let ok =
                select_h3_udp_flow_for_config(&mut outcome.controller, &open, &server_config, true)
                    .expect("gateway should select datagram mode");
            send_server_frame(
                &mut control_stream,
                &Frame::UdpFlowOk(ok.clone()),
                "udp-flow-ok",
            )
            .await;

            let close = match recv_server_frame(&mut control_stream, "udp-flow-close").await {
                Frame::UdpFlowClose(close) => close,
                other => panic!("expected udp-flow-close on control stream, got {other:?}"),
            };
            outcome
                .controller
                .close_udp_flow(close.flow_id, TransportMode::Datagram)
                .expect("closing the active datagram flow should succeed");

            let datagram = recv_h3_associated_udp_datagram(
                &mut datagram_reader,
                control_stream_id,
                ok.effective_max_payload as usize,
            )
            .await
            .expect("gateway should receive the post-close rogue datagram");
            let error = outcome
                .controller
                .validate_udp_datagram(&datagram)
                .expect_err("closed datagram flows should reject later datagrams");
            send_server_frame(
                &mut control_stream,
                &Frame::UdpFlowClose(UdpFlowClose {
                    flow_id: datagram.flow_id,
                    code: error
                        .protocol_error_code()
                        .unwrap_or(ProtocolErrorCode::ProtocolViolation),
                    message: error.to_string(),
                }),
                "udp-flow-close-reject",
            )
            .await;
            let fallback_accept = timeout(StdDuration::from_millis(250), incoming.accept()).await;
            assert!(
                !matches!(fallback_accept, Ok(Ok(Some(_)))),
                "the client must not silently open a fallback stream after a post-close datagram rejection"
            );

            finish_or_allow_h3_no_error(
                control_stream.finish().await,
                "control response should finish cleanly",
            );
            server_endpoint.wait_idle().await;
        };

        let client_future = async move {
            let connection = client_endpoint
                .connect(server_addr, "localhost")
                .expect("client connect should start")
                .await
                .expect("client quic connection should establish");
            let mut builder = client::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(client_config.datagram_runtime_enabled());
            let (mut driver, mut sender) = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("client h3 connection should initialize");
            let mut control_stream = sender
                .send_request(
                    client_config
                        .request_template(H3RequestKind::Control)
                        .expect("control request template should build")
                        .build_request()
                        .expect("control request should build"),
                )
                .await
                .expect("client should open the control request stream");
            let control_stream_id = control_stream.id();
            let mut datagram_sender = driver.get_datagram_sender(control_stream_id);
            let drive_task = tokio::spawn(async move {
                let _ = poll_fn(|cx| driver.poll_close(cx)).await;
            });

            let request_future = async move {
                send_client_frame(&mut control_stream, &client_hello, "client hello").await;
                let response = control_stream
                    .recv_response()
                    .await
                    .expect("control response headers should arrive");
                assert_eq!(response.status(), StatusCode::OK);
                match recv_client_frame(&mut control_stream, "server hello").await {
                    Frame::ServerHello(hello) => {
                        assert_eq!(hello.policy_epoch, 7);
                        assert_eq!(hello.max_udp_flows, 4);
                        assert_eq!(hello.effective_max_udp_payload, 1200);
                        assert_eq!(hello.datagram_mode, DatagramMode::AvailableAndEnabled);
                    }
                    other => panic!("expected server hello on control stream, got {other:?}"),
                }

                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowOpen(udp_open.clone()),
                    "udp-flow-open",
                )
                .await;
                let ok = match recv_client_frame(&mut control_stream, "udp-flow-ok").await {
                    Frame::UdpFlowOk(ok) => ok,
                    other => panic!("expected udp-flow-ok on control stream, got {other:?}"),
                };

                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowClose(UdpFlowClose {
                        flow_id: udp_open.flow_id,
                        code: ProtocolErrorCode::NoError,
                        message: "done".to_owned(),
                    }),
                    "udp-flow-close",
                )
                .await;
                send_h3_associated_udp_datagram(
                    &mut datagram_sender,
                    &UdpDatagram {
                        flow_id: udp_open.flow_id,
                        flags: DatagramFlags::new(0)
                            .expect("fixture datagram flags should be valid"),
                        payload: b"rogue-after-close".to_vec(),
                    },
                    ok.effective_max_payload as usize,
                )
                .expect("rogue post-close datagram should still be delivered to the carrier");

                match recv_client_frame(&mut control_stream, "udp-flow-close-reject").await {
                    Frame::UdpFlowClose(close) => {
                        assert_eq!(close.flow_id, udp_open.flow_id);
                        assert_eq!(close.code, ProtocolErrorCode::ProtocolViolation);
                        assert!(close.message.contains("not active"));
                    }
                    other => panic!("expected udp-flow-close rejection, got {other:?}"),
                }
                control_stream
                    .finish()
                    .await
                    .expect("client control request should finish");
            };

            request_future.await;
            drive_task.abort();
        };

        let (_, _) = tokio::join!(server_future, client_future);
    }))
    .await;

    result.expect("unknown-flow datagram live test should not time out");
    assert_datagram_transport_selected_without_fallback(&logs, "unknown-flow after close");
}

#[tokio::test]
async fn loopback_h3_datagrams_reject_reordered_after_close_without_fallback() {
    let (result, logs) = capture_logs_async(timeout(StdDuration::from_secs(10), async {
        let config = transport_config(true, H3DatagramRollout::Automatic);
        let (server_endpoint, cert_der) = make_server_endpoint(&config);
        let server_addr = server_endpoint
            .local_addr()
            .expect("server endpoint should have a local address");
        let client_endpoint = make_client_endpoint(&config, cert_der);
        let server_config = config.clone();
        let client_config = config.clone();
        let client_hello =
            Frame::ClientHello(sample_client_hello(mint_token(OffsetDateTime::now_utc())));
        let udp_open = localhost_target(53);

        let server_future = async move {
            let gate = GatewayPreAuthGate::new(GatewayPreAuthBudgets::default())
                .expect("default gateway pre-auth budgets should be valid");
            let connecting = server_endpoint
                .accept()
                .await
                .expect("server should accept one connection");
            let connection = connecting
                .await
                .expect("server-side quic connection should establish");
            let mut builder = server::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(true);
            let mut incoming = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("server h3 connection should initialize");
            let mut datagram_reader = incoming.get_datagram_reader();
            let resolver = incoming
                .accept()
                .await
                .expect("server should accept a control request")
                .expect("server should receive one control request");
            let (_request, mut control_stream) = resolver
                .resolve_request()
                .await
                .expect("control request should resolve");
            let control_stream_id = control_stream.send_id();

            let permit = gate
                .try_begin_hello()
                .expect("control request should fit within pending-hello budgets");
            let hello = match recv_server_frame(&mut control_stream, "control hello").await {
                Frame::ClientHello(hello) => hello,
                other => panic!("expected client hello on control stream, got {other:?}"),
            };
            permit
                .enforce_control_body_size(
                    ns_carrier_h3::encode_tunnel_frame(&Frame::ClientHello(hello.clone()))
                        .expect("hello should re-encode")
                        .len(),
                )
                .expect("hello body should stay within pre-auth limits");
            permit
                .enforce_handshake_deadline()
                .expect("hello should arrive before the handshake deadline");

            let mut outcome = admit_client_hello(
                &fixture_token_verifier(),
                &hello,
                SessionMode::Tcp,
                server_config.advertised_datagram_mode(true),
            )
            .expect("gateway admission should succeed");

            control_stream
                .send_response(
                    Response::builder()
                        .status(StatusCode::OK)
                        .body(())
                        .expect("control response should build"),
                )
                .await
                .expect("control response should send");
            send_server_frame(
                &mut control_stream,
                &Frame::ServerHello(outcome.response.clone()),
                "server hello",
            )
            .await;

            let open = match recv_server_frame(&mut control_stream, "udp-flow-open").await {
                Frame::UdpFlowOpen(open) => open,
                other => panic!("expected udp-flow-open on control stream, got {other:?}"),
            };
            let ok =
                select_h3_udp_flow_for_config(&mut outcome.controller, &open, &server_config, true)
                    .expect("gateway should select datagram mode");
            send_server_frame(
                &mut control_stream,
                &Frame::UdpFlowOk(ok.clone()),
                "udp-flow-ok",
            )
            .await;

            let close = match recv_server_frame(&mut control_stream, "udp-flow-close").await {
                Frame::UdpFlowClose(close) => close,
                other => panic!("expected udp-flow-close on control stream, got {other:?}"),
            };
            outcome
                .controller
                .close_udp_flow(close.flow_id, TransportMode::Datagram)
                .expect("closing the active datagram flow should succeed");

            let datagram = recv_h3_associated_udp_datagram(
                &mut datagram_reader,
                control_stream_id,
                ok.effective_max_payload as usize,
            )
            .await
            .expect("gateway should receive the reordered post-close datagram");
            assert_eq!(datagram.payload, b"late-before-close");
            let error = outcome
                .controller
                .validate_udp_datagram(&datagram)
                .expect_err("closed datagram flows should reject reordered datagrams that arrive after close");
            send_server_frame(
                &mut control_stream,
                &Frame::UdpFlowClose(UdpFlowClose {
                    flow_id: datagram.flow_id,
                    code: error
                        .protocol_error_code()
                        .unwrap_or(ProtocolErrorCode::ProtocolViolation),
                    message: error.to_string(),
                }),
                "udp-flow-close-reject",
            )
            .await;
            let fallback_accept = timeout(StdDuration::from_millis(250), incoming.accept()).await;
            assert!(
                !matches!(fallback_accept, Ok(Ok(Some(_)))),
                "the client must not silently open a fallback stream after a reordered post-close datagram rejection"
            );

            finish_or_allow_h3_no_error(
                control_stream.finish().await,
                "control response should finish cleanly",
            );
            server_endpoint.wait_idle().await;
        };

        let client_future = async move {
            let connection = client_endpoint
                .connect(server_addr, "localhost")
                .expect("client connect should start")
                .await
                .expect("client quic connection should establish");
            let mut builder = client::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(client_config.datagram_runtime_enabled());
            let (mut driver, mut sender) = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("client h3 connection should initialize");
            let mut control_stream = sender
                .send_request(
                    client_config
                        .request_template(H3RequestKind::Control)
                        .expect("control request template should build")
                        .build_request()
                        .expect("control request should build"),
                )
                .await
                .expect("client should open the control request stream");
            let control_stream_id = control_stream.id();
            let mut datagram_sender = driver.get_datagram_sender(control_stream_id);
            let drive_task = tokio::spawn(async move {
                let _ = poll_fn(|cx| driver.poll_close(cx)).await;
            });

            let request_future = async move {
                send_client_frame(&mut control_stream, &client_hello, "client hello").await;
                let response = control_stream
                    .recv_response()
                    .await
                    .expect("control response headers should arrive");
                assert_eq!(response.status(), StatusCode::OK);
                match recv_client_frame(&mut control_stream, "server hello").await {
                    Frame::ServerHello(hello) => {
                        assert_eq!(hello.datagram_mode, DatagramMode::AvailableAndEnabled);
                    }
                    other => panic!("expected server hello on control stream, got {other:?}"),
                }

                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowOpen(udp_open.clone()),
                    "udp-flow-open",
                )
                .await;
                let ok = match recv_client_frame(&mut control_stream, "udp-flow-ok").await {
                    Frame::UdpFlowOk(ok) => ok,
                    other => panic!("expected udp-flow-ok on control stream, got {other:?}"),
                };

                send_h3_associated_udp_datagram(
                    &mut datagram_sender,
                    &UdpDatagram {
                        flow_id: udp_open.flow_id,
                        flags: DatagramFlags::new(0)
                            .expect("fixture datagram flags should be valid"),
                        payload: b"late-before-close".to_vec(),
                    },
                    ok.effective_max_payload as usize,
                )
                .expect("client should send the datagram before closing the flow");
                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowClose(UdpFlowClose {
                        flow_id: udp_open.flow_id,
                        code: ProtocolErrorCode::NoError,
                        message: "done".to_owned(),
                    }),
                    "udp-flow-close",
                )
                .await;

                match recv_client_frame(&mut control_stream, "udp-flow-close-reject").await {
                    Frame::UdpFlowClose(close) => {
                        assert_eq!(close.flow_id, udp_open.flow_id);
                        assert_eq!(close.code, ProtocolErrorCode::ProtocolViolation);
                        assert!(close.message.contains("not active"));
                    }
                    other => panic!("expected udp-flow-close rejection, got {other:?}"),
                }
                control_stream
                    .finish()
                    .await
                    .expect("client control request should finish");
            };

            request_future.await;
            drive_task.abort();
        };

        let (_, _) = tokio::join!(server_future, client_future);
    }))
    .await;

    result.expect("reordered post-close datagram live test should not time out");
    assert_datagram_lab_profile_keeps_selected_transport(
        &logs,
        UdpWanLabProfileId::ReorderedAfterCloseRejection,
    );
    assert!(logs.contains("\"selection\":\"datagram\""));
}

#[tokio::test]
async fn loopback_udp_fallback_rejects_wrong_flow_id_with_protocol_violation_close() {
    timeout(StdDuration::from_secs(10), async {
        let config = transport_config(true, H3DatagramRollout::Disabled);
        let (server_endpoint, cert_der) = make_server_endpoint(&config);
        let server_addr = server_endpoint
            .local_addr()
            .expect("server endpoint should have a local address");
        let client_endpoint = make_client_endpoint(&config, cert_der);
        let server_config = config.clone();
        let client_config = config.clone();
        let client_hello =
            Frame::ClientHello(sample_client_hello(mint_token(OffsetDateTime::now_utc())));
        let udp_open = localhost_target(53);

        let server_future = async move {
            let gate = GatewayPreAuthGate::new(GatewayPreAuthBudgets::default())
                .expect("default gateway pre-auth budgets should be valid");
            let connecting = server_endpoint
                .accept()
                .await
                .expect("server should accept one connection");
            let connection = connecting
                .await
                .expect("server-side quic connection should establish");
            let mut builder = server::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(false);
            let mut incoming = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("server h3 connection should initialize");
            let resolver = incoming
                .accept()
                .await
                .expect("server should accept a control request")
                .expect("server should receive one control request");
            let (_request, mut control_stream) = resolver
                .resolve_request()
                .await
                .expect("control request should resolve");

            let permit = gate
                .try_begin_hello()
                .expect("control request should fit within pending-hello budgets");
            let hello = match recv_server_frame(&mut control_stream, "control hello").await {
                Frame::ClientHello(hello) => hello,
                other => panic!("expected client hello on control stream, got {other:?}"),
            };
            permit
                .enforce_control_body_size(
                    ns_carrier_h3::encode_tunnel_frame(&Frame::ClientHello(hello.clone()))
                        .expect("hello should re-encode")
                        .len(),
                )
                .expect("hello body should stay within pre-auth limits");
            permit
                .enforce_handshake_deadline()
                .expect("hello should arrive before the handshake deadline");

            let mut outcome = admit_client_hello(
                &fixture_token_verifier(),
                &hello,
                SessionMode::Tcp,
                server_config.advertised_datagram_mode(false),
            )
            .expect("gateway admission should succeed");

            control_stream
                .send_response(
                    Response::builder()
                        .status(StatusCode::OK)
                        .body(())
                        .expect("control response should build"),
                )
                .await
                .expect("control response should send");
            send_server_frame(
                &mut control_stream,
                &Frame::ServerHello(outcome.response.clone()),
                "server hello",
            )
            .await;

            let open = match recv_server_frame(&mut control_stream, "udp-flow-open").await {
                Frame::UdpFlowOpen(open) => open,
                other => panic!("expected udp-flow-open on control stream, got {other:?}"),
            };
            let ok = select_h3_udp_flow_for_config(
                &mut outcome.controller,
                &open,
                &server_config,
                false,
            )
            .expect("gateway should select stream fallback mode");
            assert_eq!(ok.transport_mode, TransportMode::StreamFallback);
            send_server_frame(&mut control_stream, &Frame::UdpFlowOk(ok), "udp-flow-ok").await;

            let fallback = incoming
                .accept()
                .await
                .expect("server should accept one fallback request")
                .expect("server should receive one fallback request");
            let (_request, mut fallback_stream) = fallback
                .resolve_request()
                .await
                .expect("fallback request should resolve");
            let stream_open = match recv_server_frame(&mut fallback_stream, "udp-stream-open").await
            {
                Frame::UdpStreamOpen(open) => open,
                other => panic!("expected udp-stream-open on fallback stream, got {other:?}"),
            };

            fallback_stream
                .send_response(
                    Response::builder()
                        .status(StatusCode::OK)
                        .body(())
                        .expect("fallback response should build"),
                )
                .await
                .expect("fallback response should send");
            let error = outcome
                .controller
                .validate_udp_fallback_stream(stream_open.flow_id)
                .expect_err("wrong fallback flow ids should be rejected");
            send_server_frame(
                &mut fallback_stream,
                &Frame::UdpStreamClose(UdpStreamClose {
                    flow_id: stream_open.flow_id,
                    code: error
                        .protocol_error_code()
                        .unwrap_or(ProtocolErrorCode::ProtocolViolation),
                    message: error.to_string(),
                }),
                "udp-stream-close-reject",
            )
            .await;
            fallback_stream
                .finish()
                .await
                .expect("fallback response should finish cleanly");

            let close = match recv_server_frame(&mut control_stream, "udp-flow-close").await {
                Frame::UdpFlowClose(close) => close,
                other => panic!("expected udp-flow-close on control stream, got {other:?}"),
            };
            outcome
                .controller
                .close_udp_flow(close.flow_id, TransportMode::StreamFallback)
                .expect("closing the original fallback flow should succeed");
            finish_or_allow_h3_no_error(
                control_stream.finish().await,
                "control response should finish cleanly",
            );
            server_endpoint.wait_idle().await;
        };

        let client_future = async move {
            let connection = client_endpoint
                .connect(server_addr, "localhost")
                .expect("client connect should start")
                .await
                .expect("client quic connection should establish");
            let mut builder = client::builder();
            builder.enable_extended_connect(true);
            builder.enable_datagram(client_config.datagram_runtime_enabled());
            let (mut driver, mut sender) = builder
                .build(H3QuinnConnection::new(connection))
                .await
                .expect("client h3 connection should initialize");
            let mut control_stream = sender
                .send_request(
                    client_config
                        .request_template(H3RequestKind::Control)
                        .expect("control request template should build")
                        .build_request()
                        .expect("control request should build"),
                )
                .await
                .expect("client should open the control request stream");
            let drive_task = tokio::spawn(async move {
                let _ = poll_fn(|cx| driver.poll_close(cx)).await;
            });

            let request_future = async move {
                send_client_frame(&mut control_stream, &client_hello, "client hello").await;
                let response = control_stream
                    .recv_response()
                    .await
                    .expect("control response headers should arrive");
                assert_eq!(response.status(), StatusCode::OK);
                match recv_client_frame(&mut control_stream, "server hello").await {
                    Frame::ServerHello(hello) => {
                        assert_eq!(hello.datagram_mode, DatagramMode::DisabledByPolicy)
                    }
                    other => panic!("expected server hello on control stream, got {other:?}"),
                }

                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowOpen(udp_open.clone()),
                    "udp-flow-open",
                )
                .await;
                let ok = match recv_client_frame(&mut control_stream, "udp-flow-ok").await {
                    Frame::UdpFlowOk(ok) => ok,
                    other => panic!("expected udp-flow-ok on control stream, got {other:?}"),
                };
                assert_eq!(ok.transport_mode, TransportMode::StreamFallback);

                let mut fallback_stream = sender
                    .send_request(
                        client_config
                            .request_template(H3RequestKind::Relay)
                            .expect("fallback request template should build")
                            .build_request()
                            .expect("fallback request should build"),
                    )
                    .await
                    .expect("client should open one fallback request stream");
                send_client_frame(
                    &mut fallback_stream,
                    &Frame::UdpStreamOpen(UdpStreamOpen {
                        flow_id: 99,
                        metadata: Vec::new(),
                    }),
                    "udp-stream-open",
                )
                .await;
                let fallback_response = fallback_stream
                    .recv_response()
                    .await
                    .expect("fallback response headers should arrive");
                assert_eq!(fallback_response.status(), StatusCode::OK);
                match recv_client_frame(&mut fallback_stream, "udp-stream-close-reject").await {
                    Frame::UdpStreamClose(close) => {
                        assert_eq!(close.flow_id, 99);
                        assert_eq!(close.code, ProtocolErrorCode::ProtocolViolation);
                        assert!(close.message.contains("not active"));
                    }
                    other => panic!("expected udp-stream-close rejection, got {other:?}"),
                }
                fallback_stream
                    .finish()
                    .await
                    .expect("fallback request should finish");

                send_client_frame(
                    &mut control_stream,
                    &Frame::UdpFlowClose(UdpFlowClose {
                        flow_id: udp_open.flow_id,
                        code: ProtocolErrorCode::NoError,
                        message: "done".to_owned(),
                    }),
                    "udp-flow-close",
                )
                .await;
                control_stream
                    .finish()
                    .await
                    .expect("client control request should finish");
            };

            request_future.await;
            drive_task.abort();
        };

        let (_, _) = tokio::join!(server_future, client_future);
    })
    .await
    .expect("wrong-flow fallback live test should not time out");
}
