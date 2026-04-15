#![forbid(unsafe_code)]

use async_trait::async_trait;
use bytes::Buf;
use bytes::Bytes;
use ed25519_dalek::pkcs8::EncodePrivateKey;
use h3::quic::{RecvStream as H3RecvStream, SendStream as H3SendStream};
use h3::{client, server};
use h3_quinn::Connection as H3QuinnConnection;
use http::{Response, StatusCode};
use ns_auth::{MintedTokenRequest, SessionTokenSigner};
use ns_carrier_h3::{
    H3ConnectBackoff, H3DatagramRollout, H3RelayRuntimeConfig, H3RequestKind, H3TransportConfig,
    H3ZeroRttPolicy, build_client_tls_config_with_roots, build_quinn_transport_config,
    decode_tunnel_frame, encode_tunnel_frame, forward_raw_tcp_relay,
};
use ns_core::{
    Capability, CarrierKind, CarrierProfileId, DatagramMode, DeviceBindingId, ManifestId,
    ProtocolErrorCode, SessionMode,
};
use ns_gateway_runtime::{
    ActiveRelayGuard, GatewayPreAuthBudgets, GatewayPreAuthGate, GatewayRelayBudgets,
    GatewayRelayGate, admit_client_hello,
};
use ns_session::{RelayStreamIo, TransportError, TransportErrorKind};
use ns_testkit::{
    FIXTURE_TOKEN_KEY_ID, fixture_token_signing_key, fixture_token_verifier, sample_client_hello,
};
use ns_wire::{
    ErrorFrame, Frame, OpenFlags, StreamAccept, StreamOpen, StreamReject, TargetAddress,
};
use quinn::crypto::rustls::{QuicClientConfig, QuicServerConfig};
use quinn::{ClientConfig, Endpoint, ServerConfig};
use rcgen::generate_simple_self_signed;
use rustls::RootCertStore;
use rustls::pki_types::{CertificateDer, PrivatePkcs8KeyDer};
use std::collections::BTreeMap;
use std::future::poll_fn;
use std::net::{Ipv4Addr, SocketAddr};
use std::sync::Arc;
use time::{Duration, OffsetDateTime};
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpListener;
use tokio::time::timeout;

fn transport_config() -> H3TransportConfig {
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
            ("x-verta-phase".to_owned(), "milestone-5".to_owned()),
        ]),
        datagram_enabled: false,
        datagram_rollout: H3DatagramRollout::Disabled,
        heartbeat_interval_ms: 20_000,
        idle_timeout_ms: 90_000,
        zero_rtt_policy: H3ZeroRttPolicy::Allow,
        connect_backoff: H3ConnectBackoff {
            initial_ms: 500,
            max_ms: 10_000,
            jitter: 0.2,
        },
    }
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

async fn start_echo_server() -> (TcpListener, SocketAddr) {
    let listener = TcpListener::bind(SocketAddr::from((Ipv4Addr::LOCALHOST, 0)))
        .await
        .expect("echo server should bind");
    let addr = listener
        .local_addr()
        .expect("echo server should have a local address");
    (listener, addr)
}

fn unsupported_relay_preamble(operation: &str) -> TransportError {
    TransportError {
        kind: TransportErrorKind::Unsupported,
        message: format!("raw relay wrapper does not support {operation}"),
    }
}

fn h3_relay_error(operation: &str, error: impl std::fmt::Display) -> TransportError {
    TransportError {
        kind: TransportErrorKind::ConnectionLost,
        message: format!("{operation} failed: {error}"),
    }
}

struct H3ServerRelayBody<S> {
    inner: server::RequestStream<S, Bytes>,
}

impl<S> H3ServerRelayBody<S> {
    fn new(inner: server::RequestStream<S, Bytes>) -> Self {
        Self { inner }
    }
}

#[async_trait]
impl<S> RelayStreamIo for H3ServerRelayBody<S>
where
    S: H3RecvStream + H3SendStream<Bytes> + Send,
{
    async fn write_preamble(&mut self, _frame: &Frame) -> Result<(), TransportError> {
        Err(unsupported_relay_preamble("write_preamble"))
    }

    async fn read_preamble(&mut self) -> Result<Frame, TransportError> {
        Err(unsupported_relay_preamble("read_preamble"))
    }

    async fn send_raw(&mut self, chunk: Bytes) -> Result<(), TransportError> {
        self.inner
            .send_data(chunk)
            .await
            .map_err(|error| h3_relay_error("server relay send_raw", error))
    }

    async fn recv_raw(&mut self) -> Result<Option<Bytes>, TransportError> {
        self.inner
            .recv_data()
            .await
            .or_else(|error| {
                if error.is_h3_no_error() {
                    Ok(None)
                } else {
                    Err(h3_relay_error("server relay recv_raw", error))
                }
            })
            .map(|maybe_chunk| maybe_chunk.map(|mut chunk| chunk.copy_to_bytes(chunk.remaining())))
    }

    async fn finish_raw(&mut self) -> Result<(), TransportError> {
        self.inner
            .finish()
            .await
            .map_err(|error| h3_relay_error("server relay finish_raw", error))
    }
}

struct H3ClientRelayBody<S> {
    inner: client::RequestStream<S, Bytes>,
}

impl<S> H3ClientRelayBody<S> {
    fn new(inner: client::RequestStream<S, Bytes>) -> Self {
        Self { inner }
    }
}

#[async_trait]
impl<S> RelayStreamIo for H3ClientRelayBody<S>
where
    S: H3RecvStream + H3SendStream<Bytes> + Send,
{
    async fn write_preamble(&mut self, _frame: &Frame) -> Result<(), TransportError> {
        Err(unsupported_relay_preamble("write_preamble"))
    }

    async fn read_preamble(&mut self) -> Result<Frame, TransportError> {
        Err(unsupported_relay_preamble("read_preamble"))
    }

    async fn send_raw(&mut self, chunk: Bytes) -> Result<(), TransportError> {
        self.inner
            .send_data(chunk)
            .await
            .map_err(|error| h3_relay_error("client relay send_raw", error))
    }

    async fn recv_raw(&mut self) -> Result<Option<Bytes>, TransportError> {
        self.inner
            .recv_data()
            .await
            .or_else(|error| {
                if error.is_h3_no_error() {
                    Ok(None)
                } else {
                    Err(h3_relay_error("client relay recv_raw", error))
                }
            })
            .map(|maybe_chunk| maybe_chunk.map(|mut chunk| chunk.copy_to_bytes(chunk.remaining())))
    }

    async fn finish_raw(&mut self) -> Result<(), TransportError> {
        self.inner
            .finish()
            .await
            .map_err(|error| h3_relay_error("client relay finish_raw", error))
    }
}

#[tokio::test]
async fn loopback_control_stream_exchanges_hello_over_real_quic_h3() {
    let config = transport_config();
    let (server_endpoint, cert_der) = make_server_endpoint(&config);
    let server_addr = server_endpoint
        .local_addr()
        .expect("server endpoint should have a local address");
    let client_endpoint = make_client_endpoint(&config, cert_der);
    let client_frame =
        Frame::ClientHello(sample_client_hello(mint_token(OffsetDateTime::now_utc())));

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
        builder.enable_datagram(config.datagram_enabled);
        let mut incoming = builder
            .build(H3QuinnConnection::new(connection))
            .await
            .expect("server h3 connection should initialize");
        let resolver = incoming
            .accept()
            .await
            .expect("server should accept a request")
            .expect("server should receive one control request");
        let (request, mut stream) = resolver
            .resolve_request()
            .await
            .expect("control request should resolve");

        assert_eq!(request.method(), http::Method::CONNECT);
        assert_eq!(request.uri().path(), "/ns/control");
        assert_eq!(
            request.uri().authority().map(|value| value.as_str()),
            Some("localhost:443")
        );
        assert_eq!(request.headers()["x-verta-profile"], "carrier-primary");

        let permit = gate
            .try_begin_hello()
            .expect("live control request should fit within pending-hello budgets");
        let mut hello_payload = stream
            .recv_data()
            .await
            .expect("control request body should be readable")
            .expect("control request should contain a hello frame");
        let hello_bytes = hello_payload.copy_to_bytes(hello_payload.remaining());
        permit
            .enforce_control_body_size(hello_bytes.len())
            .expect("hello body should stay within live pre-auth limits");
        permit
            .enforce_handshake_deadline()
            .expect("hello should arrive before the handshake deadline");
        let hello_frame =
            decode_tunnel_frame(hello_bytes.as_ref()).expect("hello frame should decode");
        let hello = match hello_frame {
            Frame::ClientHello(hello) => hello,
            other => panic!("expected client hello on control stream, got {other:?}"),
        };
        let outcome = admit_client_hello(
            &fixture_token_verifier(),
            &hello,
            SessionMode::Tcp,
            DatagramMode::Unavailable,
        )
        .expect("gateway admission should succeed over live control path");
        let response_frame = Frame::ServerHello(outcome.response.clone());

        stream
            .send_response(
                Response::builder()
                    .status(StatusCode::OK)
                    .body(())
                    .expect("response should build"),
            )
            .await
            .expect("server response should send");
        stream
            .send_data(encode_tunnel_frame(&response_frame).expect("server hello should encode"))
            .await
            .expect("server hello frame should send");
        stream
            .finish()
            .await
            .expect("control response should finish");
        server_endpoint.wait_idle().await;
        outcome.response
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
        let drive_future = async move {
            let _ = poll_fn(|cx| driver.poll_close(cx)).await;
        };
        let request_future = async move {
            let mut request_stream = sender
                .send_request(
                    config
                        .request_template(H3RequestKind::Control)
                        .expect("control request template should build")
                        .build_request()
                        .expect("control request should build"),
                )
                .await
                .expect("client should open the control request stream");
            request_stream
                .send_data(encode_tunnel_frame(&client_frame).expect("client hello should encode"))
                .await
                .expect("client hello should send");
            request_stream
                .finish()
                .await
                .expect("control request should finish");
            let response = request_stream
                .recv_response()
                .await
                .expect("control response headers should arrive");
            assert_eq!(response.status(), StatusCode::OK);
            let mut response_body = request_stream
                .recv_data()
                .await
                .expect("control response body should be readable")
                .expect("control response should contain a server hello frame");
            let response_bytes = response_body.copy_to_bytes(response_body.remaining());
            decode_tunnel_frame(response_bytes.as_ref()).expect("server hello should decode")
        };

        let (frame, _) = tokio::join!(request_future, drive_future);
        frame
    };

    let (server_hello, client_frame) = tokio::join!(server_future, client_future);
    let client_hello = match client_frame {
        Frame::ServerHello(hello) => hello,
        other => panic!("expected server hello from control stream, got {other:?}"),
    };

    assert_eq!(client_hello.policy_epoch, server_hello.policy_epoch);
    assert_eq!(client_hello.selected_version, 1);
}

#[tokio::test]
async fn loopback_relay_stream_preamble_follows_successful_hello() {
    let config = transport_config();
    let (server_endpoint, cert_der) = make_server_endpoint(&config);
    let server_addr = server_endpoint
        .local_addr()
        .expect("server endpoint should have a local address");
    let client_endpoint = make_client_endpoint(&config, cert_der);
    let client_hello =
        Frame::ClientHello(sample_client_hello(mint_token(OffsetDateTime::now_utc())));
    let relay_open = Frame::StreamOpen(StreamOpen {
        relay_id: 7,
        target: TargetAddress::Domain("relay.example.net".to_owned()),
        target_port: 443,
        flags: OpenFlags::new(0).expect("zero relay flags should be valid"),
        metadata: Vec::new(),
    });

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
        builder.enable_datagram(config.datagram_enabled);
        let mut incoming = builder
            .build(H3QuinnConnection::new(connection))
            .await
            .expect("server h3 connection should initialize");

        let control = incoming
            .accept()
            .await
            .expect("server should accept a control request")
            .expect("server should receive one control request");
        let (_control_request, mut control_stream) = control
            .resolve_request()
            .await
            .expect("control request should resolve");
        let permit = gate
            .try_begin_hello()
            .expect("control request should fit within pending-hello budgets");
        let mut hello_payload = control_stream
            .recv_data()
            .await
            .expect("control request body should be readable")
            .expect("control request should contain a hello frame");
        let hello_bytes = hello_payload.copy_to_bytes(hello_payload.remaining());
        permit
            .enforce_control_body_size(hello_bytes.len())
            .expect("hello body should stay within live pre-auth limits");
        permit
            .enforce_handshake_deadline()
            .expect("hello should arrive before the handshake deadline");
        let hello = match decode_tunnel_frame(hello_bytes.as_ref()).expect("hello should decode") {
            Frame::ClientHello(hello) => hello,
            other => panic!("expected client hello on control stream, got {other:?}"),
        };
        let mut outcome = admit_client_hello(
            &fixture_token_verifier(),
            &hello,
            SessionMode::Tcp,
            DatagramMode::Unavailable,
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
        control_stream
            .send_data(
                encode_tunnel_frame(&Frame::ServerHello(outcome.response.clone()))
                    .expect("server hello should encode"),
            )
            .await
            .expect("server hello should send");
        control_stream
            .finish()
            .await
            .expect("control response should finish");

        let relay = incoming
            .accept()
            .await
            .expect("server should accept a relay request")
            .expect("server should receive one relay request");
        let (request, mut relay_stream) = relay
            .resolve_request()
            .await
            .expect("relay request should resolve");
        assert_eq!(request.method(), http::Method::CONNECT);
        assert_eq!(request.uri().path(), "/ns/relay");
        assert_eq!(request.headers()["x-verta-profile"], "carrier-primary");

        let mut relay_payload = relay_stream
            .recv_data()
            .await
            .expect("relay request body should be readable")
            .expect("relay request should contain a preamble");
        let relay_bytes = relay_payload.copy_to_bytes(relay_payload.remaining());
        let relay_open = match decode_tunnel_frame(relay_bytes.as_ref())
            .expect("relay preamble should decode")
        {
            Frame::StreamOpen(open) => open,
            other => panic!("expected stream-open relay preamble, got {other:?}"),
        };
        outcome
            .controller
            .register_stream_open(&relay_open)
            .expect("relay preamble should be accepted after hello");
        let accept = Frame::StreamAccept(StreamAccept {
            relay_id: relay_open.relay_id,
            bind_address: TargetAddress::Domain("accepted-bind".to_owned()),
            bind_port: relay_open.target_port,
            metadata: Vec::new(),
        });

        relay_stream
            .send_response(
                Response::builder()
                    .status(StatusCode::OK)
                    .body(())
                    .expect("relay response should build"),
            )
            .await
            .expect("relay response should send");
        relay_stream
            .send_data(encode_tunnel_frame(&accept).expect("relay accept should encode"))
            .await
            .expect("relay accept should send");
        relay_stream
            .finish()
            .await
            .expect("relay response should finish");
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
        let drive_future = async move {
            let _ = poll_fn(|cx| driver.poll_close(cx)).await;
        };
        let request_future = async move {
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
            control_stream
                .send_data(encode_tunnel_frame(&client_hello).expect("client hello should encode"))
                .await
                .expect("client hello should send");
            control_stream
                .finish()
                .await
                .expect("control request should finish");
            let response = control_stream
                .recv_response()
                .await
                .expect("control response headers should arrive");
            assert_eq!(response.status(), StatusCode::OK);
            let mut control_body = control_stream
                .recv_data()
                .await
                .expect("control response body should be readable")
                .expect("control response should contain a server hello");
            let control_bytes = control_body.copy_to_bytes(control_body.remaining());
            assert!(matches!(
                decode_tunnel_frame(control_bytes.as_ref()).expect("server hello should decode"),
                Frame::ServerHello(_)
            ));

            let mut relay_stream = sender
                .send_request(
                    config
                        .request_template(H3RequestKind::Relay)
                        .expect("relay request template should build")
                        .build_request()
                        .expect("relay request should build"),
                )
                .await
                .expect("client should open the relay request stream");
            relay_stream
                .send_data(encode_tunnel_frame(&relay_open).expect("stream-open should encode"))
                .await
                .expect("stream-open should send");
            relay_stream
                .finish()
                .await
                .expect("relay request should finish");
            let response = relay_stream
                .recv_response()
                .await
                .expect("relay response headers should arrive");
            assert_eq!(response.status(), StatusCode::OK);
            let mut relay_body = relay_stream
                .recv_data()
                .await
                .expect("relay response body should be readable")
                .expect("relay response should contain a stream-accept");
            let relay_bytes = relay_body.copy_to_bytes(relay_body.remaining());
            decode_tunnel_frame(relay_bytes.as_ref()).expect("relay accept should decode")
        };

        let (frame, _) = tokio::join!(request_future, drive_future);
        frame
    };

    let (_, client_frame) = tokio::join!(server_future, client_future);
    assert!(matches!(
        client_frame,
        Frame::StreamAccept(StreamAccept { relay_id: 7, .. })
    ));
}

#[tokio::test]
async fn loopback_relay_stream_forwards_bounded_raw_bytes_after_stream_accept() {
    let config = transport_config();
    let (server_endpoint, cert_der) = make_server_endpoint(&config);
    let server_addr = server_endpoint
        .local_addr()
        .expect("server endpoint should have a local address");
    let client_endpoint = make_client_endpoint(&config, cert_der);
    let client_hello =
        Frame::ClientHello(sample_client_hello(mint_token(OffsetDateTime::now_utc())));
    let relay_open = Frame::StreamOpen(StreamOpen {
        relay_id: 7,
        target: TargetAddress::Domain("relay.example.net".to_owned()),
        target_port: 443,
        flags: OpenFlags::new(0).expect("zero relay flags should be valid"),
        metadata: Vec::new(),
    });
    let raw_chunks = vec![
        Bytes::from_static(b"verta-"),
        Bytes::from_static(b"relay-payload"),
    ];
    let expected_payload = raw_chunks
        .iter()
        .flat_map(|chunk| chunk.iter().copied())
        .collect::<Vec<_>>();
    let expected_payload_server = expected_payload.clone();
    let expected_payload_client = expected_payload.clone();

    let server_future = async move {
        let gate = GatewayPreAuthGate::new(GatewayPreAuthBudgets::default())
            .expect("default gateway pre-auth budgets should be valid");
        let relay_gate = GatewayRelayGate::new(GatewayRelayBudgets {
            max_active_relays: 1,
            max_relay_prebuffer_bytes: 4096,
            relay_idle_timeout_ms: 5_000,
        })
        .expect("relay budgets should be valid");
        let relay_runtime = H3RelayRuntimeConfig {
            max_raw_prebuffer_bytes: relay_gate.budgets().max_relay_prebuffer_bytes,
            idle_timeout_ms: relay_gate.budgets().relay_idle_timeout_ms,
            io_buffer_bytes: 1024,
        };
        let (echo_listener, echo_addr) = start_echo_server().await;
        let echo_task = tokio::spawn(async move {
            let (mut socket, _) = echo_listener
                .accept()
                .await
                .expect("echo server should accept one connection");
            let mut buffer = [0_u8; 1024];
            let mut observed_payload = Vec::new();
            loop {
                let read = socket
                    .read(&mut buffer)
                    .await
                    .expect("echo server should read bytes");
                if read == 0 {
                    break;
                }
                observed_payload.extend_from_slice(&buffer[..read]);
                socket
                    .write_all(&buffer[..read])
                    .await
                    .expect("echo server should write bytes back");
            }
            observed_payload
        });
        let connecting = server_endpoint
            .accept()
            .await
            .expect("server should accept one connection");
        let connection = connecting
            .await
            .expect("server-side quic connection should establish");
        let mut builder = server::builder();
        builder.enable_extended_connect(true);
        builder.enable_datagram(config.datagram_enabled);
        let mut incoming = builder
            .build(H3QuinnConnection::new(connection))
            .await
            .expect("server h3 connection should initialize");

        let control = incoming
            .accept()
            .await
            .expect("server should accept a control request")
            .expect("server should receive one control request");
        let (_control_request, mut control_stream) = control
            .resolve_request()
            .await
            .expect("control request should resolve");
        let permit = gate
            .try_begin_hello()
            .expect("control request should fit within pending-hello budgets");
        let mut hello_payload = control_stream
            .recv_data()
            .await
            .expect("control request body should be readable")
            .expect("control request should contain a hello frame");
        let hello_bytes = hello_payload.copy_to_bytes(hello_payload.remaining());
        permit
            .enforce_control_body_size(hello_bytes.len())
            .expect("hello body should stay within live pre-auth limits");
        permit
            .enforce_handshake_deadline()
            .expect("hello should arrive before the handshake deadline");
        let hello = match decode_tunnel_frame(hello_bytes.as_ref()).expect("hello should decode") {
            Frame::ClientHello(hello) => hello,
            other => panic!("expected client hello on control stream, got {other:?}"),
        };
        let mut outcome = admit_client_hello(
            &fixture_token_verifier(),
            &hello,
            SessionMode::Tcp,
            DatagramMode::Unavailable,
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
        control_stream
            .send_data(
                encode_tunnel_frame(&Frame::ServerHello(outcome.response.clone()))
                    .expect("server hello should encode"),
            )
            .await
            .expect("server hello should send");
        control_stream
            .finish()
            .await
            .expect("control response should finish");

        let relay = incoming
            .accept()
            .await
            .expect("server should accept a relay request")
            .expect("server should receive one relay request");
        let (_request, mut relay_stream) = relay
            .resolve_request()
            .await
            .expect("relay request should resolve");
        let mut relay_payload = relay_stream
            .recv_data()
            .await
            .expect("relay request body should be readable")
            .expect("relay request should contain a preamble");
        let relay_bytes = relay_payload.copy_to_bytes(relay_payload.remaining());
        let relay_open = match decode_tunnel_frame(relay_bytes.as_ref())
            .expect("relay preamble should decode")
        {
            Frame::StreamOpen(open) => open,
            other => panic!("expected stream-open relay preamble, got {other:?}"),
        };
        outcome
            .controller
            .register_stream_open(&relay_open)
            .expect("relay preamble should be accepted after hello");
        let accept = Frame::StreamAccept(StreamAccept {
            relay_id: relay_open.relay_id,
            bind_address: TargetAddress::Domain("accepted-bind".to_owned()),
            bind_port: relay_open.target_port,
            metadata: Vec::new(),
        });

        relay_stream
            .send_response(
                Response::builder()
                    .status(StatusCode::OK)
                    .body(())
                    .expect("relay response should build"),
            )
            .await
            .expect("relay response should send");
        relay_stream
            .send_data(encode_tunnel_frame(&accept).expect("relay accept should encode"))
            .await
            .expect("relay accept should send");

        let upstream = tokio::net::TcpStream::connect(echo_addr)
            .await
            .expect("gateway should connect to the local echo target");
        let mut relay_body = H3ServerRelayBody::new(relay_stream);
        let runtime_outcome = {
            let _relay_guard = ActiveRelayGuard::acquire(
                &mut outcome.controller,
                &relay_gate,
                relay_open.relay_id,
            )
            .expect("accepted relay should fit within gateway relay budgets");
            forward_raw_tcp_relay(
                relay_open.relay_id,
                &mut relay_body,
                upstream,
                &relay_runtime,
            )
            .await
            .expect("relay runtime should forward raw bytes over the accepted h3 relay stream")
        };
        assert!(!outcome.controller.release_relay(relay_open.relay_id));
        let observed_payload = echo_task.await.expect("echo server task should complete");
        server_endpoint.wait_idle().await;
        (runtime_outcome, observed_payload)
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
        let drive_future = async move {
            let _ = poll_fn(|cx| driver.poll_close(cx)).await;
        };
        let request_future = async move {
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
            control_stream
                .send_data(encode_tunnel_frame(&client_hello).expect("client hello should encode"))
                .await
                .expect("client hello should send");
            control_stream
                .finish()
                .await
                .expect("control request should finish");
            let response = control_stream
                .recv_response()
                .await
                .expect("control response headers should arrive");
            assert_eq!(response.status(), StatusCode::OK);
            let mut control_body = control_stream
                .recv_data()
                .await
                .expect("control response body should be readable")
                .expect("control response should contain a server hello");
            let control_bytes = control_body.copy_to_bytes(control_body.remaining());
            assert!(matches!(
                decode_tunnel_frame(control_bytes.as_ref()).expect("server hello should decode"),
                Frame::ServerHello(_)
            ));

            let mut relay_stream = sender
                .send_request(
                    config
                        .request_template(H3RequestKind::Relay)
                        .expect("relay request template should build")
                        .build_request()
                        .expect("relay request should build"),
                )
                .await
                .expect("client should open the relay request stream");
            relay_stream
                .send_data(encode_tunnel_frame(&relay_open).expect("stream-open should encode"))
                .await
                .expect("stream-open should send");
            let response = relay_stream
                .recv_response()
                .await
                .expect("relay response headers should arrive");
            assert_eq!(response.status(), StatusCode::OK);
            let mut relay_body = relay_stream
                .recv_data()
                .await
                .expect("relay response body should be readable")
                .expect("relay response should contain a stream-accept");
            let relay_bytes = relay_body.copy_to_bytes(relay_body.remaining());
            let accept =
                decode_tunnel_frame(relay_bytes.as_ref()).expect("relay accept should decode");

            let mut relay_body = H3ClientRelayBody::new(relay_stream);
            for chunk in &raw_chunks {
                relay_body
                    .send_raw(chunk.clone())
                    .await
                    .expect("raw relay payload should send");
            }
            relay_body
                .finish_raw()
                .await
                .expect("relay request body should finish after raw bytes");
            let mut echoed = Vec::new();
            let saw_clean_eof = loop {
                let maybe_chunk = timeout(std::time::Duration::from_secs(5), relay_body.recv_raw())
                    .await
                    .expect("client relay read should stay bounded")
                    .expect("client relay read should remain readable");
                let Some(chunk) = maybe_chunk else {
                    break true;
                };
                echoed.extend_from_slice(chunk.as_ref());
            };

            (accept, echoed, saw_clean_eof)
        };

        let ((accept, echoed, saw_clean_eof), _) = tokio::join!(request_future, drive_future);
        (accept, echoed, saw_clean_eof)
    };

    let ((runtime_outcome, observed_payload), (accept_frame, echoed_payload, saw_clean_eof)) =
        tokio::join!(server_future, client_future);
    assert!(matches!(
        accept_frame,
        Frame::StreamAccept(StreamAccept { relay_id: 7, .. })
    ));
    assert_eq!(
        runtime_outcome.bytes_from_client as usize,
        expected_payload_server.len()
    );
    assert_eq!(
        runtime_outcome.bytes_to_client as usize,
        expected_payload_client.len()
    );
    assert!(runtime_outcome.client_half_closed);
    assert!(runtime_outcome.upstream_half_closed);
    assert_eq!(observed_payload, expected_payload);
    assert_eq!(echoed_payload, expected_payload);
    assert!(saw_clean_eof);
}

#[tokio::test]
async fn loopback_relay_stream_handles_upstream_first_half_close_and_client_drain() {
    let config = transport_config();
    let (server_endpoint, cert_der) = make_server_endpoint(&config);
    let server_addr = server_endpoint
        .local_addr()
        .expect("server endpoint should have a local address");
    let client_endpoint = make_client_endpoint(&config, cert_der);
    let client_hello =
        Frame::ClientHello(sample_client_hello(mint_token(OffsetDateTime::now_utc())));
    let relay_open = Frame::StreamOpen(StreamOpen {
        relay_id: 9,
        target: TargetAddress::Domain("relay.example.net".to_owned()),
        target_port: 443,
        flags: OpenFlags::new(0).expect("zero relay flags should be valid"),
        metadata: Vec::new(),
    });
    let upstream_payload = b"upstream-finished-first".to_vec();
    let expected_payload = upstream_payload.clone();

    let server_future = async move {
        let gate = GatewayPreAuthGate::new(GatewayPreAuthBudgets::default())
            .expect("default gateway pre-auth budgets should be valid");
        let relay_gate = GatewayRelayGate::new(GatewayRelayBudgets {
            max_active_relays: 1,
            max_relay_prebuffer_bytes: 4096,
            relay_idle_timeout_ms: 5_000,
        })
        .expect("relay budgets should be valid");
        let relay_runtime = H3RelayRuntimeConfig {
            max_raw_prebuffer_bytes: relay_gate.budgets().max_relay_prebuffer_bytes,
            idle_timeout_ms: relay_gate.budgets().relay_idle_timeout_ms,
            io_buffer_bytes: 1024,
        };
        let upstream_listener = TcpListener::bind(SocketAddr::from((Ipv4Addr::LOCALHOST, 0)))
            .await
            .expect("upstream server should bind");
        let upstream_addr = upstream_listener
            .local_addr()
            .expect("upstream server should expose a local address");
        let upstream_task = tokio::spawn(async move {
            let (mut socket, _) = upstream_listener
                .accept()
                .await
                .expect("upstream server should accept one connection");
            socket
                .write_all(&upstream_payload)
                .await
                .expect("upstream server should write one payload");
            socket
                .shutdown()
                .await
                .expect("upstream server should half-close after writing");
        });
        let connecting = server_endpoint
            .accept()
            .await
            .expect("server should accept one connection");
        let connection = connecting
            .await
            .expect("server-side quic connection should establish");
        let mut builder = server::builder();
        builder.enable_extended_connect(true);
        builder.enable_datagram(config.datagram_enabled);
        let mut incoming = builder
            .build(H3QuinnConnection::new(connection))
            .await
            .expect("server h3 connection should initialize");

        let control = incoming
            .accept()
            .await
            .expect("server should accept a control request")
            .expect("server should receive one control request");
        let (_control_request, mut control_stream) = control
            .resolve_request()
            .await
            .expect("control request should resolve");
        let permit = gate
            .try_begin_hello()
            .expect("control request should fit within pending-hello budgets");
        let mut hello_payload = control_stream
            .recv_data()
            .await
            .expect("control request body should be readable")
            .expect("control request should contain a hello frame");
        let hello_bytes = hello_payload.copy_to_bytes(hello_payload.remaining());
        permit
            .enforce_control_body_size(hello_bytes.len())
            .expect("hello body should stay within live pre-auth limits");
        permit
            .enforce_handshake_deadline()
            .expect("hello should arrive before the handshake deadline");
        let hello = match decode_tunnel_frame(hello_bytes.as_ref()).expect("hello should decode") {
            Frame::ClientHello(hello) => hello,
            other => panic!("expected client hello on control stream, got {other:?}"),
        };
        let mut outcome = admit_client_hello(
            &fixture_token_verifier(),
            &hello,
            SessionMode::Tcp,
            DatagramMode::Unavailable,
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
        control_stream
            .send_data(
                encode_tunnel_frame(&Frame::ServerHello(outcome.response.clone()))
                    .expect("server hello should encode"),
            )
            .await
            .expect("server hello should send");
        control_stream
            .finish()
            .await
            .expect("control response should finish");

        let relay = incoming
            .accept()
            .await
            .expect("server should accept a relay request")
            .expect("server should receive one relay request");
        let (_relay_request, mut relay_stream) = relay
            .resolve_request()
            .await
            .expect("relay request should resolve");
        let mut relay_payload = relay_stream
            .recv_data()
            .await
            .expect("relay request body should be readable")
            .expect("relay request should contain a preamble");
        let relay_bytes = relay_payload.copy_to_bytes(relay_payload.remaining());
        let relay_open = match decode_tunnel_frame(relay_bytes.as_ref())
            .expect("relay preamble should decode")
        {
            Frame::StreamOpen(open) => open,
            other => panic!("expected stream-open relay preamble, got {other:?}"),
        };
        outcome
            .controller
            .register_stream_open(&relay_open)
            .expect("relay preamble should be accepted after hello");
        let accept = Frame::StreamAccept(StreamAccept {
            relay_id: relay_open.relay_id,
            bind_address: TargetAddress::Domain("accepted-bind".to_owned()),
            bind_port: relay_open.target_port,
            metadata: Vec::new(),
        });

        relay_stream
            .send_response(
                Response::builder()
                    .status(StatusCode::OK)
                    .body(())
                    .expect("relay response should build"),
            )
            .await
            .expect("relay response should send");
        relay_stream
            .send_data(encode_tunnel_frame(&accept).expect("relay accept should encode"))
            .await
            .expect("relay accept should send");

        let upstream = tokio::net::TcpStream::connect(upstream_addr)
            .await
            .expect("gateway should connect to the local upstream target");
        let mut relay_body = H3ServerRelayBody::new(relay_stream);
        let runtime_outcome = {
            let _relay_guard = ActiveRelayGuard::acquire(
                &mut outcome.controller,
                &relay_gate,
                relay_open.relay_id,
            )
            .expect("accepted relay should fit within gateway relay budgets");
            forward_raw_tcp_relay(
                relay_open.relay_id,
                &mut relay_body,
                upstream,
                &relay_runtime,
            )
            .await
            .expect("relay runtime should complete after upstream EOF")
        };
        assert!(!outcome.controller.release_relay(relay_open.relay_id));
        upstream_task.await.expect("upstream task should complete");
        server_endpoint.wait_idle().await;
        runtime_outcome
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
        let drive_future = async move {
            let _ = poll_fn(|cx| driver.poll_close(cx)).await;
        };
        let request_future = async move {
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
            control_stream
                .send_data(encode_tunnel_frame(&client_hello).expect("client hello should encode"))
                .await
                .expect("client hello should send");
            control_stream
                .finish()
                .await
                .expect("control request should finish");
            let response = control_stream
                .recv_response()
                .await
                .expect("control response headers should arrive");
            assert_eq!(response.status(), StatusCode::OK);
            let mut control_body = control_stream
                .recv_data()
                .await
                .expect("control response body should be readable")
                .expect("control response should contain a server hello");
            let control_bytes = control_body.copy_to_bytes(control_body.remaining());
            assert!(matches!(
                decode_tunnel_frame(control_bytes.as_ref()).expect("server hello should decode"),
                Frame::ServerHello(_)
            ));

            let mut relay_stream = sender
                .send_request(
                    config
                        .request_template(H3RequestKind::Relay)
                        .expect("relay request template should build")
                        .build_request()
                        .expect("relay request should build"),
                )
                .await
                .expect("client should open the relay request stream");
            relay_stream
                .send_data(encode_tunnel_frame(&relay_open).expect("stream-open should encode"))
                .await
                .expect("stream-open should send");
            let response = relay_stream
                .recv_response()
                .await
                .expect("relay response headers should arrive");
            assert_eq!(response.status(), StatusCode::OK);
            let mut relay_body = relay_stream
                .recv_data()
                .await
                .expect("relay response body should be readable")
                .expect("relay response should contain a stream-accept");
            let relay_bytes = relay_body.copy_to_bytes(relay_body.remaining());
            assert!(matches!(
                decode_tunnel_frame(relay_bytes.as_ref()).expect("relay accept should decode"),
                Frame::StreamAccept(StreamAccept { relay_id: 9, .. })
            ));

            let mut relay_body = H3ClientRelayBody::new(relay_stream);
            let mut received = Vec::new();
            loop {
                let maybe_chunk = timeout(std::time::Duration::from_secs(5), relay_body.recv_raw())
                    .await
                    .expect("client relay read should stay bounded")
                    .expect("client relay body should remain readable");
                let Some(chunk) = maybe_chunk else {
                    break;
                };
                received.extend_from_slice(chunk.as_ref());
            }
            relay_body
                .finish_raw()
                .await
                .expect("client relay request body should finish cleanly after draining");
            received
        };

        let (payload, _) = tokio::join!(request_future, drive_future);
        payload
    };

    let (runtime_outcome, received_payload) = tokio::join!(server_future, client_future);
    assert_eq!(
        runtime_outcome.close_reason,
        ns_carrier_h3::H3RelayCloseReason::UpstreamFinished
    );
    assert!(runtime_outcome.client_half_closed);
    assert!(runtime_outcome.upstream_half_closed);
    assert_eq!(runtime_outcome.bytes_from_client, 0);
    assert_eq!(
        runtime_outcome.bytes_to_client as usize,
        expected_payload.len()
    );
    assert_eq!(received_payload, expected_payload);
}

#[tokio::test]
async fn loopback_relay_stream_releases_registered_relay_after_idle_timeout() {
    let config = transport_config();
    let (server_endpoint, cert_der) = make_server_endpoint(&config);
    let server_addr = server_endpoint
        .local_addr()
        .expect("server endpoint should have a local address");
    let client_endpoint = make_client_endpoint(&config, cert_der);
    let client_hello =
        Frame::ClientHello(sample_client_hello(mint_token(OffsetDateTime::now_utc())));
    let relay_open = Frame::StreamOpen(StreamOpen {
        relay_id: 13,
        target: TargetAddress::Domain("relay.example.net".to_owned()),
        target_port: 443,
        flags: OpenFlags::new(0).expect("zero relay flags should be valid"),
        metadata: Vec::new(),
    });

    let server_future = async move {
        let gate = GatewayPreAuthGate::new(GatewayPreAuthBudgets::default())
            .expect("default gateway pre-auth budgets should be valid");
        let relay_gate = GatewayRelayGate::new(GatewayRelayBudgets {
            max_active_relays: 1,
            max_relay_prebuffer_bytes: 4096,
            relay_idle_timeout_ms: 75,
        })
        .expect("relay budgets should be valid");
        let relay_runtime = H3RelayRuntimeConfig {
            max_raw_prebuffer_bytes: relay_gate.budgets().max_relay_prebuffer_bytes,
            idle_timeout_ms: relay_gate.budgets().relay_idle_timeout_ms,
            io_buffer_bytes: 1024,
        };
        let upstream_listener = TcpListener::bind(SocketAddr::from((Ipv4Addr::LOCALHOST, 0)))
            .await
            .expect("idle upstream server should bind");
        let upstream_addr = upstream_listener
            .local_addr()
            .expect("idle upstream server should expose a local address");
        let upstream_task = tokio::spawn(async move {
            let (_socket, _) = upstream_listener
                .accept()
                .await
                .expect("idle upstream server should accept one connection");
            tokio::time::sleep(std::time::Duration::from_millis(250)).await;
        });
        let connecting = server_endpoint
            .accept()
            .await
            .expect("server should accept one connection");
        let connection = connecting
            .await
            .expect("server-side quic connection should establish");
        let mut builder = server::builder();
        builder.enable_extended_connect(true);
        builder.enable_datagram(config.datagram_enabled);
        let mut incoming = builder
            .build(H3QuinnConnection::new(connection))
            .await
            .expect("server h3 connection should initialize");

        let control = incoming
            .accept()
            .await
            .expect("server should accept a control request")
            .expect("server should receive one control request");
        let (_control_request, mut control_stream) = control
            .resolve_request()
            .await
            .expect("control request should resolve");
        let permit = gate
            .try_begin_hello()
            .expect("control request should fit within pending-hello budgets");
        let mut hello_payload = control_stream
            .recv_data()
            .await
            .expect("control request body should be readable")
            .expect("control request should contain a hello frame");
        let hello_bytes = hello_payload.copy_to_bytes(hello_payload.remaining());
        permit
            .enforce_control_body_size(hello_bytes.len())
            .expect("hello body should stay within live pre-auth limits");
        permit
            .enforce_handshake_deadline()
            .expect("hello should arrive before the handshake deadline");
        let hello = match decode_tunnel_frame(hello_bytes.as_ref()).expect("hello should decode") {
            Frame::ClientHello(hello) => hello,
            other => panic!("expected client hello on control stream, got {other:?}"),
        };
        let mut outcome = admit_client_hello(
            &fixture_token_verifier(),
            &hello,
            SessionMode::Tcp,
            DatagramMode::Unavailable,
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
        control_stream
            .send_data(
                encode_tunnel_frame(&Frame::ServerHello(outcome.response.clone()))
                    .expect("server hello should encode"),
            )
            .await
            .expect("server hello should send");
        control_stream
            .finish()
            .await
            .expect("control response should finish");

        let relay = incoming
            .accept()
            .await
            .expect("server should accept a relay request")
            .expect("server should receive one relay request");
        let (_relay_request, mut relay_stream) = relay
            .resolve_request()
            .await
            .expect("relay request should resolve");
        let mut relay_payload = relay_stream
            .recv_data()
            .await
            .expect("relay request body should be readable")
            .expect("relay request should contain a preamble");
        let relay_bytes = relay_payload.copy_to_bytes(relay_payload.remaining());
        let relay_open = match decode_tunnel_frame(relay_bytes.as_ref())
            .expect("relay preamble should decode")
        {
            Frame::StreamOpen(open) => open,
            other => panic!("expected stream-open relay preamble, got {other:?}"),
        };
        outcome
            .controller
            .register_stream_open(&relay_open)
            .expect("relay preamble should be accepted after hello");

        relay_stream
            .send_response(
                Response::builder()
                    .status(StatusCode::OK)
                    .body(())
                    .expect("relay response should build"),
            )
            .await
            .expect("relay response should send");
        relay_stream
            .send_data(
                encode_tunnel_frame(&Frame::StreamAccept(StreamAccept {
                    relay_id: relay_open.relay_id,
                    bind_address: TargetAddress::Domain("accepted-bind".to_owned()),
                    bind_port: relay_open.target_port,
                    metadata: Vec::new(),
                }))
                .expect("relay accept should encode"),
            )
            .await
            .expect("relay accept should send");

        let upstream = tokio::net::TcpStream::connect(upstream_addr)
            .await
            .expect("gateway should connect to the idle upstream target");
        let mut relay_body = H3ServerRelayBody::new(relay_stream);
        let error = {
            let _relay_guard = ActiveRelayGuard::acquire(
                &mut outcome.controller,
                &relay_gate,
                relay_open.relay_id,
            )
            .expect("accepted relay should fit within gateway relay budgets");
            forward_raw_tcp_relay(
                relay_open.relay_id,
                &mut relay_body,
                upstream,
                &relay_runtime,
            )
            .await
            .expect_err("idle relay should time out")
        };
        assert_eq!(error.kind, TransportErrorKind::TimedOut);
        assert!(!outcome.controller.release_relay(relay_open.relay_id));
        upstream_task
            .await
            .expect("idle upstream task should complete");
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
        let drive_future = async move {
            let _ = poll_fn(|cx| driver.poll_close(cx)).await;
        };
        let request_future = async move {
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
            control_stream
                .send_data(encode_tunnel_frame(&client_hello).expect("client hello should encode"))
                .await
                .expect("client hello should send");
            control_stream
                .finish()
                .await
                .expect("control request should finish");
            let response = control_stream
                .recv_response()
                .await
                .expect("control response headers should arrive");
            assert_eq!(response.status(), StatusCode::OK);
            let mut control_body = control_stream
                .recv_data()
                .await
                .expect("control response body should be readable")
                .expect("control response should contain a server hello");
            let control_bytes = control_body.copy_to_bytes(control_body.remaining());
            assert!(matches!(
                decode_tunnel_frame(control_bytes.as_ref()).expect("server hello should decode"),
                Frame::ServerHello(_)
            ));

            let mut relay_stream = sender
                .send_request(
                    config
                        .request_template(H3RequestKind::Relay)
                        .expect("relay request template should build")
                        .build_request()
                        .expect("relay request should build"),
                )
                .await
                .expect("client should open the relay request stream");
            relay_stream
                .send_data(encode_tunnel_frame(&relay_open).expect("stream-open should encode"))
                .await
                .expect("stream-open should send");
            let response = relay_stream
                .recv_response()
                .await
                .expect("relay response headers should arrive");
            assert_eq!(response.status(), StatusCode::OK);
            let mut relay_body = relay_stream
                .recv_data()
                .await
                .expect("relay response body should be readable")
                .expect("relay response should contain a stream-accept");
            let relay_bytes = relay_body.copy_to_bytes(relay_body.remaining());
            assert!(matches!(
                decode_tunnel_frame(relay_bytes.as_ref()).expect("relay accept should decode"),
                Frame::StreamAccept(StreamAccept { relay_id: 13, .. })
            ));

            tokio::time::sleep(std::time::Duration::from_millis(200)).await;
        };

        let (_, _) = tokio::join!(request_future, drive_future);
    };

    let (_, _) = tokio::join!(server_future, client_future);
}

#[tokio::test]
async fn loopback_relay_stream_surfaces_live_overload_with_frozen_flow_limit_error() {
    let config = transport_config();
    let (server_endpoint, cert_der) = make_server_endpoint(&config);
    let server_addr = server_endpoint
        .local_addr()
        .expect("server endpoint should have a local address");
    let client_endpoint = make_client_endpoint(&config, cert_der);
    let client_hello =
        Frame::ClientHello(sample_client_hello(mint_token(OffsetDateTime::now_utc())));
    let relay_one = Frame::StreamOpen(StreamOpen {
        relay_id: 21,
        target: TargetAddress::Domain("relay.example.net".to_owned()),
        target_port: 443,
        flags: OpenFlags::new(0).expect("zero relay flags should be valid"),
        metadata: Vec::new(),
    });
    let relay_two = Frame::StreamOpen(StreamOpen {
        relay_id: 22,
        ..match relay_one.clone() {
            Frame::StreamOpen(open) => open,
            _ => unreachable!(),
        }
    });

    let server_future = async move {
        let gate = GatewayPreAuthGate::new(GatewayPreAuthBudgets::default())
            .expect("default gateway pre-auth budgets should be valid");
        let relay_gate = GatewayRelayGate::new(GatewayRelayBudgets {
            max_active_relays: 1,
            max_relay_prebuffer_bytes: 4096,
            relay_idle_timeout_ms: 5_000,
        })
        .expect("relay budgets should be valid");
        let connecting = server_endpoint
            .accept()
            .await
            .expect("server should accept one connection");
        let connection = connecting
            .await
            .expect("server-side quic connection should establish");
        let mut builder = server::builder();
        builder.enable_extended_connect(true);
        builder.enable_datagram(config.datagram_enabled);
        let mut incoming = builder
            .build(H3QuinnConnection::new(connection))
            .await
            .expect("server h3 connection should initialize");

        let control = incoming
            .accept()
            .await
            .expect("server should accept a control request")
            .expect("server should receive one control request");
        let (_control_request, mut control_stream) = control
            .resolve_request()
            .await
            .expect("control request should resolve");
        let permit = gate
            .try_begin_hello()
            .expect("control request should fit within pending-hello budgets");
        let mut hello_payload = control_stream
            .recv_data()
            .await
            .expect("control request body should be readable")
            .expect("control request should contain a hello frame");
        let hello_bytes = hello_payload.copy_to_bytes(hello_payload.remaining());
        permit
            .enforce_control_body_size(hello_bytes.len())
            .expect("hello body should stay within live pre-auth limits");
        permit
            .enforce_handshake_deadline()
            .expect("hello should arrive before the handshake deadline");
        let hello = match decode_tunnel_frame(hello_bytes.as_ref()).expect("hello should decode") {
            Frame::ClientHello(hello) => hello,
            other => panic!("expected client hello on control stream, got {other:?}"),
        };
        let mut outcome = admit_client_hello(
            &fixture_token_verifier(),
            &hello,
            SessionMode::Tcp,
            DatagramMode::Unavailable,
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
        control_stream
            .send_data(
                encode_tunnel_frame(&Frame::ServerHello(outcome.response.clone()))
                    .expect("server hello should encode"),
            )
            .await
            .expect("server hello should send");
        control_stream
            .finish()
            .await
            .expect("control response should finish");

        let first_relay = incoming
            .accept()
            .await
            .expect("server should accept the first relay request")
            .expect("server should receive the first relay request");
        let (_first_request, mut first_stream) = first_relay
            .resolve_request()
            .await
            .expect("first relay request should resolve");
        let mut first_payload = first_stream
            .recv_data()
            .await
            .expect("first relay request body should be readable")
            .expect("first relay request should contain a preamble");
        let first_bytes = first_payload.copy_to_bytes(first_payload.remaining());
        let relay_one = match decode_tunnel_frame(first_bytes.as_ref())
            .expect("first relay preamble should decode")
        {
            Frame::StreamOpen(open) => open,
            other => panic!("expected first stream-open relay preamble, got {other:?}"),
        };
        outcome
            .controller
            .register_stream_open(&relay_one)
            .expect("first relay should register");
        first_stream
            .send_response(
                Response::builder()
                    .status(StatusCode::OK)
                    .body(())
                    .expect("first relay response should build"),
            )
            .await
            .expect("first relay response should send");
        first_stream
            .send_data(
                encode_tunnel_frame(&Frame::StreamAccept(StreamAccept {
                    relay_id: relay_one.relay_id,
                    bind_address: TargetAddress::Domain("accepted-bind".to_owned()),
                    bind_port: relay_one.target_port,
                    metadata: Vec::new(),
                }))
                .expect("first relay accept should encode"),
            )
            .await
            .expect("first relay accept should send");

        let first_permit = relay_gate
            .try_begin_relay()
            .expect("first relay should consume the only active relay permit");

        let second_relay = incoming
            .accept()
            .await
            .expect("server should accept the second relay request")
            .expect("server should receive the second relay request");
        let (_second_request, mut second_stream) = second_relay
            .resolve_request()
            .await
            .expect("second relay request should resolve");
        let mut second_payload = second_stream
            .recv_data()
            .await
            .expect("second relay request body should be readable")
            .expect("second relay request should contain a preamble");
        let second_bytes = second_payload.copy_to_bytes(second_payload.remaining());
        let relay_two = match decode_tunnel_frame(second_bytes.as_ref())
            .expect("second relay preamble should decode")
        {
            Frame::StreamOpen(open) => open,
            other => panic!("expected second stream-open relay preamble, got {other:?}"),
        };
        outcome
            .controller
            .register_stream_open(&relay_two)
            .expect("second relay should register before runtime budget admission");
        let overload =
            ActiveRelayGuard::acquire(&mut outcome.controller, &relay_gate, relay_two.relay_id)
                .expect_err("second relay should hit the active relay budget");
        assert_eq!(
            overload.pre_auth_protocol_error_code(),
            Some(ProtocolErrorCode::FlowLimitReached)
        );
        assert!(outcome.controller.release_relay(relay_two.relay_id));

        second_stream
            .send_response(
                Response::builder()
                    .status(StatusCode::TOO_MANY_REQUESTS)
                    .body(())
                    .expect("overload response should build"),
            )
            .await
            .expect("overload response should send");
        second_stream
            .send_data(
                encode_tunnel_frame(&Frame::StreamReject(StreamReject {
                    relay_id: relay_two.relay_id,
                    code: overload
                        .pre_auth_protocol_error_code()
                        .expect("overload should map to a protocol error"),
                    retryable: true,
                    message: overload.to_string(),
                    metadata: Vec::new(),
                }))
                .expect("overload stream-reject frame should encode"),
            )
            .await
            .expect("overload stream-reject frame should send");
        second_stream
            .finish()
            .await
            .expect("overload response should finish");

        drop(first_permit);
        assert!(outcome.controller.release_relay(relay_one.relay_id));
        assert!(!outcome.controller.release_relay(relay_one.relay_id));
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
        let drive_future = async move {
            let _ = poll_fn(|cx| driver.poll_close(cx)).await;
        };
        let request_future = async move {
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
            control_stream
                .send_data(encode_tunnel_frame(&client_hello).expect("client hello should encode"))
                .await
                .expect("client hello should send");
            control_stream
                .finish()
                .await
                .expect("control request should finish");
            let response = control_stream
                .recv_response()
                .await
                .expect("control response headers should arrive");
            assert_eq!(response.status(), StatusCode::OK);
            let mut control_body = control_stream
                .recv_data()
                .await
                .expect("control response body should be readable")
                .expect("control response should contain a server hello");
            let control_bytes = control_body.copy_to_bytes(control_body.remaining());
            assert!(matches!(
                decode_tunnel_frame(control_bytes.as_ref()).expect("server hello should decode"),
                Frame::ServerHello(_)
            ));

            let mut first_stream = sender
                .send_request(
                    config
                        .request_template(H3RequestKind::Relay)
                        .expect("first relay request template should build")
                        .build_request()
                        .expect("first relay request should build"),
                )
                .await
                .expect("client should open the first relay request stream");
            first_stream
                .send_data(
                    encode_tunnel_frame(&relay_one).expect("first stream-open should encode"),
                )
                .await
                .expect("first stream-open should send");
            let first_response = first_stream
                .recv_response()
                .await
                .expect("first relay response headers should arrive");
            assert_eq!(first_response.status(), StatusCode::OK);
            let mut first_body = first_stream
                .recv_data()
                .await
                .expect("first relay response body should be readable")
                .expect("first relay response should contain a stream-accept");
            let first_bytes = first_body.copy_to_bytes(first_body.remaining());
            assert!(matches!(
                decode_tunnel_frame(first_bytes.as_ref())
                    .expect("first relay accept should decode"),
                Frame::StreamAccept(StreamAccept { relay_id: 21, .. })
            ));

            let mut second_stream = sender
                .send_request(
                    config
                        .request_template(H3RequestKind::Relay)
                        .expect("second relay request template should build")
                        .build_request()
                        .expect("second relay request should build"),
                )
                .await
                .expect("client should open the second relay request stream");
            second_stream
                .send_data(
                    encode_tunnel_frame(&relay_two).expect("second stream-open should encode"),
                )
                .await
                .expect("second stream-open should send");
            let second_response = second_stream
                .recv_response()
                .await
                .expect("second relay response headers should arrive");
            assert_eq!(second_response.status(), StatusCode::TOO_MANY_REQUESTS);
            let mut second_body = second_stream
                .recv_data()
                .await
                .expect("second relay response body should be readable")
                .expect("second relay response should contain a stream reject");
            let second_bytes = second_body.copy_to_bytes(second_body.remaining());
            assert!(matches!(
                decode_tunnel_frame(second_bytes.as_ref())
                    .expect("overload stream-reject should decode"),
                Frame::StreamReject(StreamReject {
                    relay_id: 22,
                    code: ProtocolErrorCode::FlowLimitReached,
                    retryable: true,
                    ..
                })
            ));

            first_stream
                .finish()
                .await
                .expect("first relay request should finish cleanly after overload coverage");
        };

        let (_, _) = tokio::join!(request_future, drive_future);
    };

    let (_, _) = tokio::join!(server_future, client_future);
}

#[tokio::test]
async fn loopback_control_stream_rejects_invalid_token_before_session_open() {
    let config = transport_config();
    let (server_endpoint, cert_der) = make_server_endpoint(&config);
    let server_addr = server_endpoint
        .local_addr()
        .expect("server endpoint should have a local address");
    let client_endpoint = make_client_endpoint(&config, cert_der);
    let client_frame = Frame::ClientHello(sample_client_hello("not-a-valid-jwt".to_owned()));

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
        let mut incoming = builder
            .build(H3QuinnConnection::new(connection))
            .await
            .expect("server h3 connection should initialize");
        let resolver = incoming
            .accept()
            .await
            .expect("server should accept a request")
            .expect("server should receive one control request");
        let (_request, mut stream) = resolver
            .resolve_request()
            .await
            .expect("control request should resolve");
        let permit = gate
            .try_begin_hello()
            .expect("live control request should fit within pending-hello budgets");
        let mut hello_payload = stream
            .recv_data()
            .await
            .expect("control request body should be readable")
            .expect("control request should contain a hello frame");
        let hello_bytes = hello_payload.copy_to_bytes(hello_payload.remaining());
        permit
            .enforce_control_body_size(hello_bytes.len())
            .expect("hello body should stay within live pre-auth limits");
        permit
            .enforce_handshake_deadline()
            .expect("hello should arrive before the handshake deadline");
        let hello = match decode_tunnel_frame(hello_bytes.as_ref()).expect("hello should decode") {
            Frame::ClientHello(hello) => hello,
            other => panic!("expected client hello on control stream, got {other:?}"),
        };
        let error = admit_client_hello(
            &fixture_token_verifier(),
            &hello,
            SessionMode::Tcp,
            DatagramMode::Unavailable,
        )
        .expect_err("invalid token should be rejected");

        stream
            .send_response(
                Response::builder()
                    .status(StatusCode::UNAUTHORIZED)
                    .body(())
                    .expect("response should build"),
            )
            .await
            .expect("error response should send");
        stream
            .send_data(
                encode_tunnel_frame(&Frame::Error(ErrorFrame {
                    code: ProtocolErrorCode::AuthFailed,
                    message: error.to_string(),
                    is_terminal: true,
                    details: Vec::new(),
                }))
                .expect("error frame should encode"),
            )
            .await
            .expect("error frame should send");
        stream.finish().await.expect("error response should finish");
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
        let (mut driver, mut sender) = builder
            .build(H3QuinnConnection::new(connection))
            .await
            .expect("client h3 connection should initialize");
        let drive_future = async move {
            let _ = poll_fn(|cx| driver.poll_close(cx)).await;
        };
        let request_future = async move {
            let mut request_stream = sender
                .send_request(
                    config
                        .request_template(H3RequestKind::Control)
                        .expect("control request template should build")
                        .build_request()
                        .expect("control request should build"),
                )
                .await
                .expect("client should open the control request stream");
            request_stream
                .send_data(encode_tunnel_frame(&client_frame).expect("client hello should encode"))
                .await
                .expect("client hello should send");
            request_stream
                .finish()
                .await
                .expect("control request should finish");
            let response = request_stream
                .recv_response()
                .await
                .expect("error response headers should arrive");
            assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
            let mut response_body = request_stream
                .recv_data()
                .await
                .expect("error response body should be readable")
                .expect("error response should contain an error frame");
            let response_bytes = response_body.copy_to_bytes(response_body.remaining());
            decode_tunnel_frame(response_bytes.as_ref()).expect("error frame should decode")
        };

        let (frame, _) = tokio::join!(request_future, drive_future);
        frame
    };

    let (_, response_frame) = tokio::join!(server_future, client_future);
    assert!(matches!(
        response_frame,
        Frame::Error(ErrorFrame {
            code: ProtocolErrorCode::AuthFailed,
            is_terminal: true,
            ..
        })
    ));
}

#[tokio::test]
async fn loopback_control_stream_rejects_oversized_hello_before_admission() {
    let config = transport_config();
    let (server_endpoint, cert_der) = make_server_endpoint(&config);
    let server_addr = server_endpoint
        .local_addr()
        .expect("server endpoint should have a local address");
    let client_endpoint = make_client_endpoint(&config, cert_der);
    let client_frame =
        Frame::ClientHello(sample_client_hello(mint_token(OffsetDateTime::now_utc())));

    let server_future = async move {
        let gate = GatewayPreAuthGate::new(GatewayPreAuthBudgets {
            max_pending_hellos: 1,
            max_control_body_bytes: 8,
            handshake_deadline_ms: 5_000,
        })
        .expect("test budgets should be valid");
        let connecting = server_endpoint
            .accept()
            .await
            .expect("server should accept one connection");
        let connection = connecting
            .await
            .expect("server-side quic connection should establish");
        let mut builder = server::builder();
        builder.enable_extended_connect(true);
        let mut incoming = builder
            .build(H3QuinnConnection::new(connection))
            .await
            .expect("server h3 connection should initialize");
        let resolver = incoming
            .accept()
            .await
            .expect("server should accept a request")
            .expect("server should receive one control request");
        let (_request, mut stream) = resolver
            .resolve_request()
            .await
            .expect("control request should resolve");
        let permit = gate
            .try_begin_hello()
            .expect("control request should fit within pending-hello budgets");
        let mut hello_payload = stream
            .recv_data()
            .await
            .expect("control request body should be readable")
            .expect("control request should contain a hello frame");
        let hello_bytes = hello_payload.copy_to_bytes(hello_payload.remaining());
        let error = permit
            .enforce_control_body_size(hello_bytes.len())
            .expect_err("oversized hello body should be rejected");

        stream
            .send_response(
                Response::builder()
                    .status(StatusCode::PAYLOAD_TOO_LARGE)
                    .body(())
                    .expect("response should build"),
            )
            .await
            .expect("error response should send");
        stream
            .send_data(
                encode_tunnel_frame(&Frame::Error(ErrorFrame {
                    code: error
                        .pre_auth_protocol_error_code()
                        .expect("oversized hello should map to a protocol error"),
                    message: error.to_string(),
                    is_terminal: true,
                    details: Vec::new(),
                }))
                .expect("error frame should encode"),
            )
            .await
            .expect("error frame should send");
        stream.finish().await.expect("error response should finish");
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
        let (mut driver, mut sender) = builder
            .build(H3QuinnConnection::new(connection))
            .await
            .expect("client h3 connection should initialize");
        let drive_future = async move {
            let _ = poll_fn(|cx| driver.poll_close(cx)).await;
        };
        let request_future = async move {
            let mut request_stream = sender
                .send_request(
                    config
                        .request_template(H3RequestKind::Control)
                        .expect("control request template should build")
                        .build_request()
                        .expect("control request should build"),
                )
                .await
                .expect("client should open the control request stream");
            request_stream
                .send_data(encode_tunnel_frame(&client_frame).expect("client hello should encode"))
                .await
                .expect("client hello should send");
            request_stream
                .finish()
                .await
                .expect("control request should finish");
            let response = request_stream
                .recv_response()
                .await
                .expect("error response headers should arrive");
            assert_eq!(response.status(), StatusCode::PAYLOAD_TOO_LARGE);
            let mut response_body = request_stream
                .recv_data()
                .await
                .expect("error response body should be readable")
                .expect("error response should contain an error frame");
            let response_bytes = response_body.copy_to_bytes(response_body.remaining());
            decode_tunnel_frame(response_bytes.as_ref()).expect("error frame should decode")
        };

        let (frame, _) = tokio::join!(request_future, drive_future);
        frame
    };

    let (_, response_frame) = tokio::join!(server_future, client_future);
    assert!(matches!(
        response_frame,
        Frame::Error(ErrorFrame {
            code: ProtocolErrorCode::FrameTooLarge,
            is_terminal: true,
            ..
        })
    ));
}
