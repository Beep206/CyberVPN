use std::{
    net::SocketAddr,
    sync::{Arc, OnceLock},
    time::Duration,
};

use helix_runtime::{
    crypto::{
        client_proof, decrypt_frame, derive_session_key, encrypt_frame, random_nonce,
        unix_timestamp_ms, Direction,
    },
    model::{HandshakeHello, HandshakeWelcome, PROTOCOL_MAGIC, PROTOCOL_VERSION},
    spawn_client, spawn_server, ClientConfig, ClientHandle, ControlFrame, ServerConfig,
    ServerHandle, StreamTarget, TransportRoute,
};
use tokio::{
    io::{copy_bidirectional, AsyncReadExt, AsyncWriteExt},
    net::{TcpListener, TcpStream},
    sync::{mpsc, oneshot, Mutex, OwnedMutexGuard},
    task::JoinHandle,
    time::timeout,
};

fn session_test_mutex() -> Arc<Mutex<()>> {
    static SESSION_TEST_MUTEX: OnceLock<Arc<Mutex<()>>> = OnceLock::new();
    SESSION_TEST_MUTEX
        .get_or_init(|| Arc::new(Mutex::new(())))
        .clone()
}

async fn acquire_session_test_guard() -> OwnedMutexGuard<()> {
    session_test_mutex().lock_owned().await
}

async fn shutdown_test_session(client: &ClientHandle, server: &ServerHandle) {
    let mut fixture_tasks = Vec::new();
    shutdown_test_session_with_fixtures(client, server, &mut fixture_tasks).await;
}

async fn shutdown_test_session_with_fixtures(
    client: &ClientHandle,
    server: &ServerHandle,
    fixture_tasks: &mut Vec<JoinHandle<()>>,
) {
    client.shutdown().await;
    server.shutdown().await;

    for task in fixture_tasks.drain(..) {
        task.abort();
        let _ = task.await;
    }

    let deadline = tokio::time::Instant::now() + Duration::from_secs(2);
    loop {
        let client_snapshot = client.snapshot().await;
        let server_snapshot = server.snapshot().await;
        let client_quiet = !client_snapshot.ready
            && !client_snapshot.connected
            && client_snapshot.active_streams == 0
            && client_snapshot.pending_open_streams == 0;
        let server_quiet =
            server_snapshot.active_sessions == 0 && server_snapshot.active_streams == 0;

        if client_quiet && server_quiet {
            break;
        }

        if tokio::time::Instant::now() >= deadline {
            break;
        }

        tokio::time::sleep(Duration::from_millis(25)).await;
    }

    tokio::time::sleep(Duration::from_millis(50)).await;
}

struct RawSession {
    stream: TcpStream,
    session_key: [u8; 32],
    outgoing_seq: u64,
    incoming_seq: u64,
    welcome: HandshakeWelcome,
}

async fn raw_handshake(server_addr: SocketAddr, resume_session_id: Option<String>) -> RawSession {
    let mut stream = TcpStream::connect(server_addr).await.expect("raw connect");
    let client_nonce = random_nonce();
    let mut hello = HandshakeHello {
        magic: PROTOCOL_MAGIC.to_string(),
        protocol_version: PROTOCOL_VERSION,
        manifest_id: "manifest-1".to_string(),
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        route_ref: "node-lab-01".to_string(),
        resume_session_id,
        client_nonce,
        timestamp_ms: unix_timestamp_ms(),
        proof: [0_u8; 32],
    };
    hello.proof = client_proof("shared-session-token", &hello).expect("client proof");
    write_json_frame(&mut stream, &hello).await;
    let welcome = read_json_frame::<HandshakeWelcome>(&mut stream).await;
    assert!(
        welcome.accepted,
        "raw handshake rejected: {:?}",
        welcome.error
    );
    let session_key = derive_session_key(
        "shared-session-token",
        &welcome.session_id,
        "ptp-lab-edge-v2",
        &hello.client_nonce,
        &welcome.server_nonce,
    )
    .expect("derive session key");

    RawSession {
        stream,
        session_key,
        outgoing_seq: 0,
        incoming_seq: 0,
        welcome,
    }
}

async fn raw_write_control_frame(session: &mut RawSession, frame: &ControlFrame) {
    write_encrypted_frame(
        &mut session.stream,
        &session.session_key,
        Direction::ClientToServer,
        &mut session.outgoing_seq,
        frame,
    )
    .await;
}

async fn raw_read_control_frame(session: &mut RawSession) -> ControlFrame {
    read_encrypted_frame(
        &mut session.stream,
        &session.session_key,
        Direction::ServerToClient,
        &mut session.incoming_seq,
    )
    .await
}

async fn write_json_frame<T: serde::Serialize>(stream: &mut TcpStream, value: &T) {
    let payload = serde_json::to_vec(value).expect("serialize json frame");
    let len = u32::try_from(payload.len()).expect("json frame length");
    stream.write_u32(len).await.expect("write json len");
    stream
        .write_all(&payload)
        .await
        .expect("write json payload");
}

async fn read_json_frame<T: serde::de::DeserializeOwned>(stream: &mut TcpStream) -> T {
    let len = stream.read_u32().await.expect("read json len");
    let mut payload = vec![0_u8; usize::try_from(len).expect("json len usize")];
    stream
        .read_exact(&mut payload)
        .await
        .expect("read json payload");
    serde_json::from_slice(&payload).expect("decode json frame")
}

async fn write_encrypted_frame(
    stream: &mut TcpStream,
    session_key: &[u8; 32],
    direction: Direction,
    sequence: &mut u64,
    frame: &ControlFrame,
) {
    let ciphertext =
        encrypt_frame(session_key, direction, *sequence, frame).expect("encrypt control frame");
    let len = u32::try_from(ciphertext.len()).expect("ciphertext length");
    stream.write_u64(*sequence).await.expect("write seq");
    stream.write_u32(len).await.expect("write cipher len");
    stream
        .write_all(&ciphertext)
        .await
        .expect("write ciphertext");
    *sequence = sequence.saturating_add(1);
}

async fn read_encrypted_frame(
    stream: &mut TcpStream,
    session_key: &[u8; 32],
    direction: Direction,
    expected_sequence: &mut u64,
) -> ControlFrame {
    let sequence = stream.read_u64().await.expect("read seq");
    assert_eq!(sequence, *expected_sequence, "unexpected frame sequence");
    let len = stream.read_u32().await.expect("read cipher len");
    let mut ciphertext = vec![0_u8; usize::try_from(len).expect("cipher len usize")];
    stream
        .read_exact(&mut ciphertext)
        .await
        .expect("read ciphertext");
    let frame =
        decrypt_frame(session_key, direction, sequence, &ciphertext).expect("decrypt frame");
    *expected_sequence = expected_sequence.saturating_add(1);
    frame
}

#[derive(Clone)]
struct InterruptibleProxy {
    bridge_task: Arc<Mutex<Option<JoinHandle<()>>>>,
}

impl InterruptibleProxy {
    async fn drop_active_connection(&self) {
        let task = self.bridge_task.lock().await.take();
        if let Some(task) = task {
            task.abort();
            let _ = task.await;
        }
    }
}

async fn spawn_interruptible_proxy(
    target_addr: SocketAddr,
) -> (SocketAddr, InterruptibleProxy, JoinHandle<()>) {
    let listener = TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind interruptible proxy");
    let proxy_addr = listener.local_addr().expect("proxy addr");
    let bridge_task = Arc::new(Mutex::new(None));
    let bridge_task_ref = bridge_task.clone();

    let accept_task = tokio::spawn(async move {
        loop {
            let Ok((mut downstream, _)) = listener.accept().await else {
                break;
            };

            let bridge = tokio::spawn(async move {
                let Ok(mut upstream) = tokio::net::TcpStream::connect(target_addr).await else {
                    return;
                };
                let _ = copy_bidirectional(&mut downstream, &mut upstream).await;
            });

            let previous = bridge_task_ref.lock().await.replace(bridge);
            if let Some(previous) = previous {
                previous.abort();
                let _ = previous.await;
            }
        }
    });

    (proxy_addr, InterruptibleProxy { bridge_task }, accept_task)
}

#[tokio::test]
async fn client_and_server_exchange_encrypted_heartbeats() {
    let _test_guard = acquire_session_test_guard().await;

    let server = spawn_server(ServerConfig {
        bind_addrs: vec!["127.0.0.1:0".parse::<SocketAddr>().expect("bind addr")],
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "shared-session-token".to_string(),
        heartbeat_timeout: Duration::from_secs(2),
        allow_private_targets: true,
    })
    .await
    .expect("spawn server");

    let bound_addr = server
        .snapshot()
        .await
        .bound_addrs
        .first()
        .cloned()
        .expect("bound addr");
    let parsed_addr = bound_addr.parse::<SocketAddr>().expect("socket addr");

    let client = spawn_client(ClientConfig {
        manifest_id: "manifest-1".to_string(),
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "shared-session-token".to_string(),
        route: TransportRoute {
            endpoint_ref: "node-lab-01".to_string(),
            dial_host: parsed_addr.ip().to_string(),
            dial_port: parsed_addr.port(),
            server_name: None,
            preference: 10,
            policy_tag: "primary".to_string(),
        },
        connect_timeout: Duration::from_secs(2),
        heartbeat_interval: Duration::from_millis(150),
        reconnect_delay: Duration::from_millis(100),
    });

    wait_until(
        || async {
            let snapshot = client.snapshot().await;
            snapshot.ready && snapshot.last_ping_rtt_ms.is_some()
        },
        Duration::from_secs(3),
    )
    .await;

    let client_snapshot = client.snapshot().await;
    let server_snapshot = server.snapshot().await;

    assert!(client_snapshot.ready);
    assert!(client_snapshot.connected);
    assert!(client_snapshot.last_ping_rtt_ms.is_some());
    assert!(server_snapshot.successful_handshakes >= 1);
    assert!(server_snapshot.frames_in >= 1);
    assert!(server_snapshot.frames_out >= 1);

    shutdown_test_session(&client, &server).await;
}

#[tokio::test]
async fn client_surfaces_authentication_failure_with_wrong_token() {
    let _test_guard = acquire_session_test_guard().await;

    let server = spawn_server(ServerConfig {
        bind_addrs: vec!["127.0.0.1:0".parse::<SocketAddr>().expect("bind addr")],
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "server-token".to_string(),
        heartbeat_timeout: Duration::from_secs(2),
        allow_private_targets: true,
    })
    .await
    .expect("spawn server");

    let bound_addr = server
        .snapshot()
        .await
        .bound_addrs
        .first()
        .cloned()
        .expect("bound addr");
    let parsed_addr = bound_addr.parse::<SocketAddr>().expect("socket addr");

    let client = spawn_client(ClientConfig {
        manifest_id: "manifest-1".to_string(),
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "wrong-token".to_string(),
        route: TransportRoute {
            endpoint_ref: "node-lab-01".to_string(),
            dial_host: parsed_addr.ip().to_string(),
            dial_port: parsed_addr.port(),
            server_name: None,
            preference: 10,
            policy_tag: "primary".to_string(),
        },
        connect_timeout: Duration::from_secs(2),
        heartbeat_interval: Duration::from_millis(150),
        reconnect_delay: Duration::from_millis(100),
    });

    wait_until(
        || async {
            let snapshot = client.snapshot().await;
            snapshot.last_error.is_some() && !snapshot.ready
        },
        Duration::from_secs(3),
    )
    .await;

    let client_snapshot = client.snapshot().await;
    let server_snapshot = server.snapshot().await;

    assert!(!client_snapshot.ready);
    assert!(client_snapshot.last_error.is_some());
    assert!(server_snapshot.failed_handshakes >= 1);

    shutdown_test_session(&client, &server).await;
}

#[tokio::test]
async fn raw_client_resumes_detached_session_and_receives_queued_tail_data() {
    let _test_guard = acquire_session_test_guard().await;

    let upstream_listener = TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind resumable upstream");
    let upstream_addr = upstream_listener.local_addr().expect("upstream addr");
    let (upstream_tx, upstream_rx) = oneshot::channel::<mpsc::Sender<Vec<u8>>>();
    let upstream_task = tokio::spawn(async move {
        let Ok((mut stream, _)) = upstream_listener.accept().await else {
            return;
        };
        let (tx, mut rx) = mpsc::channel::<Vec<u8>>(8);
        let _ = upstream_tx.send(tx);
        while let Some(chunk) = rx.recv().await {
            if stream.write_all(&chunk).await.is_err() {
                break;
            }
        }
    });

    let server = spawn_server(ServerConfig {
        bind_addrs: vec!["127.0.0.1:0".parse::<SocketAddr>().expect("bind addr")],
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "shared-session-token".to_string(),
        heartbeat_timeout: Duration::from_secs(2),
        allow_private_targets: true,
    })
    .await
    .expect("spawn server");

    let bound_addr = server
        .snapshot()
        .await
        .bound_addrs
        .first()
        .cloned()
        .expect("bound addr");
    let parsed_addr = bound_addr.parse::<SocketAddr>().expect("socket addr");

    let mut first_session = raw_handshake(parsed_addr, None).await;
    raw_write_control_frame(
        &mut first_session,
        &ControlFrame::StreamOpen {
            stream_id: 1,
            target_host: upstream_addr.ip().to_string(),
            target_port: upstream_addr.port(),
        },
    )
    .await;

    let opened = raw_read_control_frame(&mut first_session).await;
    match opened {
        ControlFrame::StreamOpened { stream_id, .. } => assert_eq!(stream_id, 1),
        other => panic!("expected stream opened, got {other:?}"),
    }

    let original_session_id = first_session.welcome.session_id.clone();
    let upstream_sender = upstream_rx.await.expect("upstream sender");
    drop(first_session);

    upstream_sender
        .send(b"queued-after-disconnect".to_vec())
        .await
        .expect("queue upstream payload");

    tokio::time::sleep(Duration::from_millis(150)).await;

    let mut resumed_session = raw_handshake(parsed_addr, Some(original_session_id.clone())).await;
    assert!(
        resumed_session.welcome.resumed,
        "server did not resume detached session"
    );
    assert_eq!(resumed_session.welcome.session_id, original_session_id);

    raw_write_control_frame(
        &mut resumed_session,
        &ControlFrame::Ping {
            sent_at_ms: unix_timestamp_ms(),
        },
    )
    .await;

    let resumed_frame = timeout(Duration::from_secs(3), async {
        loop {
            match raw_read_control_frame(&mut resumed_session).await {
                ControlFrame::Pong { .. } => continue,
                other => break other,
            }
        }
    })
    .await
    .expect("resumed frame timeout");
    match resumed_frame {
        ControlFrame::StreamData { stream_id, data } => {
            assert_eq!(stream_id, 1);
            assert_eq!(data, b"queued-after-disconnect".to_vec());
        }
        other => panic!("expected resumed stream data, got {other:?}"),
    }

    raw_write_control_frame(
        &mut resumed_session,
        &ControlFrame::Close {
            reason: "test-complete".to_string(),
        },
    )
    .await;
    drop(resumed_session);
    drop(upstream_sender);
    upstream_task.abort();
    let _ = upstream_task.await;
    server.shutdown().await;
}

#[tokio::test]
async fn client_and_server_forward_stream_data_over_secure_session() {
    let _test_guard = acquire_session_test_guard().await;
    let mut fixture_tasks = Vec::new();

    let upstream_listener = TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind upstream echo");
    let upstream_addr = upstream_listener.local_addr().expect("upstream addr");
    fixture_tasks.push(tokio::spawn(async move {
        loop {
            let Ok((mut stream, _)) = upstream_listener.accept().await else {
                break;
            };
            tokio::spawn(async move {
                let mut buffer = [0_u8; 4096];
                loop {
                    match stream.read(&mut buffer).await {
                        Ok(0) => break,
                        Ok(read) => {
                            if stream.write_all(&buffer[..read]).await.is_err() {
                                break;
                            }
                        }
                        Err(_) => break,
                    }
                }
            });
        }
    }));

    let server = spawn_server(ServerConfig {
        bind_addrs: vec!["127.0.0.1:0".parse::<SocketAddr>().expect("bind addr")],
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "shared-session-token".to_string(),
        heartbeat_timeout: Duration::from_secs(2),
        allow_private_targets: true,
    })
    .await
    .expect("spawn server");

    let bound_addr = server
        .snapshot()
        .await
        .bound_addrs
        .first()
        .cloned()
        .expect("bound addr");
    let parsed_addr = bound_addr.parse::<SocketAddr>().expect("socket addr");

    let client = spawn_client(ClientConfig {
        manifest_id: "manifest-1".to_string(),
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "shared-session-token".to_string(),
        route: TransportRoute {
            endpoint_ref: "node-lab-01".to_string(),
            dial_host: parsed_addr.ip().to_string(),
            dial_port: parsed_addr.port(),
            server_name: None,
            preference: 10,
            policy_tag: "primary".to_string(),
        },
        connect_timeout: Duration::from_secs(2),
        heartbeat_interval: Duration::from_millis(150),
        reconnect_delay: Duration::from_millis(100),
    });

    wait_until(
        || async {
            let snapshot = client.snapshot().await;
            snapshot.ready
        },
        Duration::from_secs(3),
    )
    .await;

    let mut stream = client
        .open_stream(StreamTarget::new(
            upstream_addr.ip().to_string(),
            upstream_addr.port(),
        ))
        .await
        .expect("open remote stream");

    let writer = stream.writer();
    writer
        .send(b"cybervpn-secure-stream".to_vec())
        .await
        .expect("send secure payload");
    let echoed = stream.recv().await.expect("echoed payload");
    assert_eq!(echoed, b"cybervpn-secure-stream".to_vec());

    writer.close("test-complete").await.expect("close stream");
    shutdown_test_session_with_fixtures(&client, &server, &mut fixture_tasks).await;
}

#[tokio::test]
async fn client_resumes_same_session_and_keeps_active_stream_alive_after_transport_drop() {
    let _test_guard = acquire_session_test_guard().await;
    let mut fixture_tasks = Vec::new();

    let upstream_listener = TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind upstream echo");
    let upstream_addr = upstream_listener.local_addr().expect("upstream addr");
    fixture_tasks.push(tokio::spawn(async move {
        loop {
            let Ok((mut stream, _)) = upstream_listener.accept().await else {
                break;
            };
            tokio::spawn(async move {
                let mut buffer = [0_u8; 4096];
                loop {
                    match stream.read(&mut buffer).await {
                        Ok(0) => break,
                        Ok(read) => {
                            if stream.write_all(&buffer[..read]).await.is_err() {
                                break;
                            }
                        }
                        Err(_) => break,
                    }
                }
            });
        }
    }));

    let server = spawn_server(ServerConfig {
        bind_addrs: vec!["127.0.0.1:0".parse::<SocketAddr>().expect("bind addr")],
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "shared-session-token".to_string(),
        heartbeat_timeout: Duration::from_secs(2),
        allow_private_targets: true,
    })
    .await
    .expect("spawn server");

    let server_addr = server
        .snapshot()
        .await
        .bound_addrs
        .first()
        .cloned()
        .expect("bound addr")
        .parse::<SocketAddr>()
        .expect("socket addr");

    let (proxy_addr, proxy, proxy_task) = spawn_interruptible_proxy(server_addr).await;
    fixture_tasks.push(proxy_task);

    let client = spawn_client(ClientConfig {
        manifest_id: "manifest-1".to_string(),
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "shared-session-token".to_string(),
        route: TransportRoute {
            endpoint_ref: "node-lab-01".to_string(),
            dial_host: proxy_addr.ip().to_string(),
            dial_port: proxy_addr.port(),
            server_name: None,
            preference: 10,
            policy_tag: "primary".to_string(),
        },
        connect_timeout: Duration::from_secs(2),
        heartbeat_interval: Duration::from_millis(150),
        reconnect_delay: Duration::from_millis(100),
    });

    wait_until(
        || async {
            let snapshot = client.snapshot().await;
            snapshot.ready && snapshot.connected
        },
        Duration::from_secs(3),
    )
    .await;

    let mut stream = client
        .open_stream(StreamTarget::new(
            upstream_addr.ip().to_string(),
            upstream_addr.port(),
        ))
        .await
        .expect("open remote stream");

    let writer = stream.writer();
    writer
        .send(b"before-resume".to_vec())
        .await
        .expect("send before resume");
    let echoed = stream.recv().await.expect("echo before resume");
    assert_eq!(echoed, b"before-resume".to_vec());

    let previous_session_id = client
        .snapshot()
        .await
        .session_id
        .expect("existing session id");

    proxy.drop_active_connection().await;

    wait_until(
        || async {
            let snapshot = client.snapshot().await;
            snapshot.ready
                && snapshot.connected
                && snapshot.resumed_last_session
                && snapshot.session_id.as_deref() == Some(previous_session_id.as_str())
        },
        Duration::from_secs(5),
    )
    .await;

    writer
        .send(b"after-resume".to_vec())
        .await
        .expect("send after resume");
    let echoed = stream.recv().await.expect("echo after resume");
    assert_eq!(echoed, b"after-resume".to_vec());

    shutdown_test_session_with_fixtures(&client, &server, &mut fixture_tasks).await;
}

#[tokio::test]
async fn client_prioritizes_interactive_streams_while_bulk_transfer_is_active() {
    let _test_guard = acquire_session_test_guard().await;
    let mut fixture_tasks = Vec::new();

    let sink_listener = TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind sink upstream");
    let sink_addr = sink_listener.local_addr().expect("sink addr");
    fixture_tasks.push(tokio::spawn(async move {
        loop {
            let Ok((mut stream, _)) = sink_listener.accept().await else {
                break;
            };
            tokio::spawn(async move {
                let mut buffer = [0_u8; 16 * 1024];
                loop {
                    match stream.read(&mut buffer).await {
                        Ok(0) => break,
                        Ok(_) => {
                            tokio::time::sleep(Duration::from_millis(1)).await;
                        }
                        Err(_) => break,
                    }
                }
            });
        }
    }));

    let echo_listener = TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind echo upstream");
    let echo_addr = echo_listener.local_addr().expect("echo addr");
    fixture_tasks.push(tokio::spawn(async move {
        loop {
            let Ok((mut stream, _)) = echo_listener.accept().await else {
                break;
            };
            tokio::spawn(async move {
                let mut buffer = [0_u8; 4096];
                loop {
                    match stream.read(&mut buffer).await {
                        Ok(0) => break,
                        Ok(read) => {
                            if stream.write_all(&buffer[..read]).await.is_err() {
                                break;
                            }
                        }
                        Err(_) => break,
                    }
                }
            });
        }
    }));

    let server = spawn_server(ServerConfig {
        bind_addrs: vec!["127.0.0.1:0".parse::<SocketAddr>().expect("bind addr")],
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "shared-session-token".to_string(),
        heartbeat_timeout: Duration::from_secs(2),
        allow_private_targets: true,
    })
    .await
    .expect("spawn server");

    let bound_addr = server
        .snapshot()
        .await
        .bound_addrs
        .first()
        .cloned()
        .expect("bound addr");
    let parsed_addr = bound_addr.parse::<SocketAddr>().expect("socket addr");

    let client = spawn_client(ClientConfig {
        manifest_id: "manifest-1".to_string(),
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "shared-session-token".to_string(),
        route: TransportRoute {
            endpoint_ref: "node-lab-01".to_string(),
            dial_host: parsed_addr.ip().to_string(),
            dial_port: parsed_addr.port(),
            server_name: None,
            preference: 10,
            policy_tag: "primary".to_string(),
        },
        connect_timeout: Duration::from_secs(2),
        heartbeat_interval: Duration::from_millis(150),
        reconnect_delay: Duration::from_millis(100),
    });

    wait_until(
        || async {
            let snapshot = client.snapshot().await;
            snapshot.ready
        },
        Duration::from_secs(3),
    )
    .await;

    let bulk_stream = client
        .open_stream(StreamTarget::new(
            sink_addr.ip().to_string(),
            sink_addr.port(),
        ))
        .await
        .expect("open bulk stream");
    let bulk_writer = bulk_stream.writer();
    let bulk_payload = vec![0x5a_u8; 64 * 1024];
    let bulk_task = tokio::spawn(async move {
        for _ in 0..128 {
            bulk_writer
                .send(bulk_payload.clone())
                .await
                .expect("send bulk payload");
        }
        bulk_writer
            .close("bulk-complete")
            .await
            .expect("close bulk");
    });

    tokio::time::sleep(Duration::from_millis(20)).await;

    let open_started = std::time::Instant::now();
    let mut interactive_stream = timeout(
        Duration::from_secs(1),
        client.open_stream(StreamTarget::new(
            echo_addr.ip().to_string(),
            echo_addr.port(),
        )),
    )
    .await
    .expect("interactive open timeout")
    .expect("interactive stream");
    let open_latency_ms = open_started.elapsed().as_millis();

    let writer = interactive_stream.writer();
    let first_byte_started = std::time::Instant::now();
    writer
        .send(b"latency-probe".to_vec())
        .await
        .expect("send probe");
    let echoed = timeout(Duration::from_secs(1), interactive_stream.recv())
        .await
        .expect("interactive recv timeout")
        .expect("interactive recv");
    let first_byte_latency_ms = first_byte_started.elapsed().as_millis();

    assert_eq!(echoed, b"latency-probe".to_vec());
    assert!(
        open_latency_ms <= 300,
        "interactive stream open took too long under bulk load: {open_latency_ms} ms"
    );
    assert!(
        first_byte_latency_ms <= 500,
        "interactive first-byte took too long under bulk load: {first_byte_latency_ms} ms"
    );

    eprintln!(
        "Helix interactive-under-load: open={}ms first-byte={}ms",
        open_latency_ms, first_byte_latency_ms
    );

    writer
        .close("interactive-complete")
        .await
        .expect("close probe");
    bulk_task.await.expect("bulk task");
    shutdown_test_session_with_fixtures(&client, &server, &mut fixture_tasks).await;
}

#[tokio::test]
async fn client_close_flushes_buffered_stream_data_before_stream_close() {
    let _test_guard = acquire_session_test_guard().await;

    let payload = vec![0x7f_u8; 64 * 1024];
    let expected_total = payload.len() * 64;
    let (total_bytes_tx, total_bytes_rx) = oneshot::channel();
    let upstream_listener = TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind upstream sink");
    let upstream_addr = upstream_listener.local_addr().expect("upstream addr");
    let expected_total_for_sink = expected_total;
    tokio::spawn(async move {
        let Ok((mut stream, _)) = upstream_listener.accept().await else {
            return;
        };
        let mut total_bytes = 0_usize;
        let mut buffer = [0_u8; 16 * 1024];
        loop {
            match stream.read(&mut buffer).await {
                Ok(0) => break,
                Ok(read) => {
                    total_bytes = total_bytes.saturating_add(read);
                    if total_bytes >= expected_total_for_sink {
                        let _ = total_bytes_tx.send(total_bytes);
                        return;
                    }
                }
                Err(_) => break,
            }
        }
    });

    let server = spawn_server(ServerConfig {
        bind_addrs: vec!["127.0.0.1:0".parse::<SocketAddr>().expect("bind addr")],
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "shared-session-token".to_string(),
        heartbeat_timeout: Duration::from_secs(2),
        allow_private_targets: true,
    })
    .await
    .expect("spawn server");

    let bound_addr = server
        .snapshot()
        .await
        .bound_addrs
        .first()
        .cloned()
        .expect("bound addr");
    let parsed_addr = bound_addr.parse::<SocketAddr>().expect("socket addr");

    let client = spawn_client(ClientConfig {
        manifest_id: "manifest-1".to_string(),
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "shared-session-token".to_string(),
        route: TransportRoute {
            endpoint_ref: "node-lab-01".to_string(),
            dial_host: parsed_addr.ip().to_string(),
            dial_port: parsed_addr.port(),
            server_name: None,
            preference: 10,
            policy_tag: "primary".to_string(),
        },
        connect_timeout: Duration::from_secs(2),
        heartbeat_interval: Duration::from_millis(150),
        reconnect_delay: Duration::from_millis(100),
    });

    wait_until(
        || async {
            let snapshot = client.snapshot().await;
            snapshot.ready
        },
        Duration::from_secs(3),
    )
    .await;

    let stream = client
        .open_stream(StreamTarget::new(
            upstream_addr.ip().to_string(),
            upstream_addr.port(),
        ))
        .await
        .expect("open remote stream");
    let writer = stream.writer();

    for _ in 0..64 {
        writer
            .send(payload.clone())
            .await
            .expect("send buffered payload");
    }
    writer
        .close("flush-before-close")
        .await
        .expect("close stream");

    let total_bytes = timeout(Duration::from_secs(10), total_bytes_rx)
        .await
        .expect("upstream total timeout")
        .expect("upstream total");

    assert_eq!(
        total_bytes, expected_total,
        "server observed truncated payload before stream close"
    );

    shutdown_test_session(&client, &server).await;
}

#[tokio::test]
async fn client_drains_server_tail_data_before_stream_close() {
    let _test_guard = acquire_session_test_guard().await;

    let chunk = vec![0x42_u8; 16 * 1024];
    let expected_chunks = 64_usize;
    let expected_total = chunk.len() * expected_chunks;
    let upstream_listener = TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind upstream source");
    let upstream_addr = upstream_listener.local_addr().expect("upstream addr");
    tokio::spawn(async move {
        let Ok((mut stream, _)) = upstream_listener.accept().await else {
            return;
        };
        for _ in 0..expected_chunks {
            if stream.write_all(&chunk).await.is_err() {
                return;
            }
        }
        let _ = stream.shutdown().await;
    });

    let server = spawn_server(ServerConfig {
        bind_addrs: vec!["127.0.0.1:0".parse::<SocketAddr>().expect("bind addr")],
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "shared-session-token".to_string(),
        heartbeat_timeout: Duration::from_secs(2),
        allow_private_targets: true,
    })
    .await
    .expect("spawn server");

    let bound_addr = server
        .snapshot()
        .await
        .bound_addrs
        .first()
        .cloned()
        .expect("bound addr");
    let parsed_addr = bound_addr.parse::<SocketAddr>().expect("socket addr");

    let client = spawn_client(ClientConfig {
        manifest_id: "manifest-1".to_string(),
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "shared-session-token".to_string(),
        route: TransportRoute {
            endpoint_ref: "node-lab-01".to_string(),
            dial_host: parsed_addr.ip().to_string(),
            dial_port: parsed_addr.port(),
            server_name: None,
            preference: 10,
            policy_tag: "primary".to_string(),
        },
        connect_timeout: Duration::from_secs(2),
        heartbeat_interval: Duration::from_millis(150),
        reconnect_delay: Duration::from_millis(100),
    });

    wait_until(
        || async {
            let snapshot = client.snapshot().await;
            snapshot.ready
        },
        Duration::from_secs(3),
    )
    .await;

    let mut stream = client
        .open_stream(StreamTarget::new(
            upstream_addr.ip().to_string(),
            upstream_addr.port(),
        ))
        .await
        .expect("open remote stream");

    tokio::time::sleep(Duration::from_millis(150)).await;

    let mut total_bytes = 0_usize;
    loop {
        match timeout(Duration::from_secs(2), stream.recv()).await {
            Ok(Some(data)) => {
                total_bytes = total_bytes.saturating_add(data.len());
            }
            Ok(None) => break,
            Err(_) => panic!("timed out waiting for downstream tail data"),
        }
    }

    assert_eq!(
        total_bytes, expected_total,
        "client observed truncated downstream payload before stream close"
    );
    assert!(client.snapshot().await.ready);

    shutdown_test_session(&client, &server).await;
}

#[tokio::test]
async fn client_finish_preserves_server_response_after_local_half_close() {
    let _test_guard = acquire_session_test_guard().await;

    let upstream_listener = TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind upstream");
    let upstream_addr = upstream_listener.local_addr().expect("upstream addr");
    tokio::spawn(async move {
        let Ok((mut stream, _)) = upstream_listener.accept().await else {
            return;
        };

        let mut request = Vec::new();
        stream
            .read_to_end(&mut request)
            .await
            .expect("read request to eof");
        assert!(
            request.starts_with(b"GET /half-close HTTP/1.1\r\n"),
            "unexpected upstream request: {:?}",
            String::from_utf8_lossy(&request)
        );

        let response = b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\nConnection: close\r\n\r\nhello";
        stream.write_all(response).await.expect("write response");
        let _ = stream.shutdown().await;
    });

    let server = spawn_server(ServerConfig {
        bind_addrs: vec!["127.0.0.1:0".parse::<SocketAddr>().expect("bind addr")],
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "shared-session-token".to_string(),
        heartbeat_timeout: Duration::from_secs(2),
        allow_private_targets: true,
    })
    .await
    .expect("spawn server");

    let bound_addr = server
        .snapshot()
        .await
        .bound_addrs
        .first()
        .cloned()
        .expect("bound addr");
    let parsed_addr = bound_addr.parse::<SocketAddr>().expect("socket addr");

    let client = spawn_client(ClientConfig {
        manifest_id: "manifest-1".to_string(),
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "shared-session-token".to_string(),
        route: TransportRoute {
            endpoint_ref: "node-lab-01".to_string(),
            dial_host: parsed_addr.ip().to_string(),
            dial_port: parsed_addr.port(),
            server_name: None,
            preference: 10,
            policy_tag: "primary".to_string(),
        },
        connect_timeout: Duration::from_secs(2),
        heartbeat_interval: Duration::from_millis(150),
        reconnect_delay: Duration::from_millis(100),
    });

    wait_until(
        || async {
            let snapshot = client.snapshot().await;
            snapshot.ready
        },
        Duration::from_secs(3),
    )
    .await;

    let mut stream = client
        .open_stream(StreamTarget::new(
            upstream_addr.ip().to_string(),
            upstream_addr.port(),
        ))
        .await
        .expect("open stream");
    let writer = stream.writer();
    writer
        .send(b"GET /half-close HTTP/1.1\r\nHost: half-close\r\nConnection: close\r\n\r\n".to_vec())
        .await
        .expect("send request");
    writer.finish().await.expect("finish request uplink");

    let mut response = Vec::new();
    loop {
        match timeout(Duration::from_secs(2), stream.recv()).await {
            Ok(Some(chunk)) => response.extend_from_slice(&chunk),
            Ok(None) => break,
            Err(_) => panic!("timed out waiting for half-close response"),
        }
    }

    assert!(
        response.starts_with(b"HTTP/1.1 200 OK\r\n"),
        "unexpected response start: {:?}",
        String::from_utf8_lossy(&response)
    );
    assert!(
        response.ends_with(b"hello"),
        "expected response body after uplink finish, got {:?}",
        String::from_utf8_lossy(&response)
    );

    shutdown_test_session(&client, &server).await;
}

#[tokio::test]
async fn client_finish_preserves_large_server_response_after_local_half_close() {
    let _test_guard = acquire_session_test_guard().await;

    let response_chunk = vec![0x61_u8; 16 * 1024];
    let response_chunks = 64_usize;
    let response_body_len = response_chunk.len() * response_chunks;

    let upstream_listener = TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind upstream");
    let upstream_addr = upstream_listener.local_addr().expect("upstream addr");
    tokio::spawn(async move {
        let Ok((mut stream, _)) = upstream_listener.accept().await else {
            return;
        };

        let mut request = Vec::new();
        stream
            .read_to_end(&mut request)
            .await
            .expect("read request to eof");
        assert!(
            request.starts_with(b"GET /half-close-large HTTP/1.1\r\n"),
            "unexpected upstream request: {:?}",
            String::from_utf8_lossy(&request)
        );

        let header = format!(
            "HTTP/1.1 200 OK\r\nContent-Length: {response_body_len}\r\nConnection: close\r\n\r\n"
        );
        stream
            .write_all(header.as_bytes())
            .await
            .expect("write response header");
        for _ in 0..response_chunks {
            stream
                .write_all(&response_chunk)
                .await
                .expect("write response body chunk");
        }
        let _ = stream.shutdown().await;
    });

    let server = spawn_server(ServerConfig {
        bind_addrs: vec!["127.0.0.1:0".parse::<SocketAddr>().expect("bind addr")],
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "shared-session-token".to_string(),
        heartbeat_timeout: Duration::from_secs(2),
        allow_private_targets: true,
    })
    .await
    .expect("spawn server");

    let bound_addr = server
        .snapshot()
        .await
        .bound_addrs
        .first()
        .cloned()
        .expect("bound addr");
    let parsed_addr = bound_addr.parse::<SocketAddr>().expect("socket addr");

    let client = spawn_client(ClientConfig {
        manifest_id: "manifest-1".to_string(),
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "shared-session-token".to_string(),
        route: TransportRoute {
            endpoint_ref: "node-lab-01".to_string(),
            dial_host: parsed_addr.ip().to_string(),
            dial_port: parsed_addr.port(),
            server_name: None,
            preference: 10,
            policy_tag: "primary".to_string(),
        },
        connect_timeout: Duration::from_secs(2),
        heartbeat_interval: Duration::from_millis(150),
        reconnect_delay: Duration::from_millis(100),
    });

    wait_until(
        || async {
            let snapshot = client.snapshot().await;
            snapshot.ready
        },
        Duration::from_secs(3),
    )
    .await;

    let mut stream = client
        .open_stream(StreamTarget::new(
            upstream_addr.ip().to_string(),
            upstream_addr.port(),
        ))
        .await
        .expect("open stream");
    let writer = stream.writer();
    writer
        .send(
            b"GET /half-close-large HTTP/1.1\r\nHost: half-close-large\r\nConnection: close\r\n\r\n"
                .to_vec(),
        )
        .await
        .expect("send request");
    writer.finish().await.expect("finish request uplink");

    let mut response = Vec::new();
    loop {
        match timeout(Duration::from_secs(3), stream.recv()).await {
            Ok(Some(chunk)) => response.extend_from_slice(&chunk),
            Ok(None) => break,
            Err(_) => panic!("timed out waiting for large half-close response"),
        }
    }

    let header = format!(
        "HTTP/1.1 200 OK\r\nContent-Length: {response_body_len}\r\nConnection: close\r\n\r\n"
    );
    assert!(
        response.starts_with(header.as_bytes()),
        "unexpected response start: {} bytes {:?}",
        response.len(),
        String::from_utf8_lossy(&response[..response.len().min(128)])
    );
    assert_eq!(
        response.len(),
        header.len() + response_body_len,
        "expected full large response after uplink finish; client_snapshot={:?}; server_snapshot={:?}",
        client.snapshot().await,
        server.snapshot().await
    );

    shutdown_test_session(&client, &server).await;
}

#[tokio::test]
async fn client_inbound_scheduler_keeps_probe_streams_responsive_when_sibling_receiver_stalls() {
    let _test_guard = acquire_session_test_guard().await;
    let mut fixture_tasks = Vec::new();

    let flood_listener = TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind flood upstream");
    let flood_addr = flood_listener.local_addr().expect("flood addr");
    fixture_tasks.push(tokio::spawn(async move {
        loop {
            let Ok((mut stream, _)) = flood_listener.accept().await else {
                break;
            };
            tokio::spawn(async move {
                let payload = vec![0x3c_u8; 16 * 1024];
                loop {
                    if stream.write_all(&payload).await.is_err() {
                        break;
                    }
                }
            });
        }
    }));

    let echo_listener = TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind echo upstream");
    let echo_addr = echo_listener.local_addr().expect("echo addr");
    fixture_tasks.push(tokio::spawn(async move {
        loop {
            let Ok((mut stream, _)) = echo_listener.accept().await else {
                break;
            };
            tokio::spawn(async move {
                let mut buffer = [0_u8; 4096];
                loop {
                    match stream.read(&mut buffer).await {
                        Ok(0) => break,
                        Ok(read) => {
                            if stream.write_all(&buffer[..read]).await.is_err() {
                                break;
                            }
                        }
                        Err(_) => break,
                    }
                }
            });
        }
    }));

    let server = spawn_server(ServerConfig {
        bind_addrs: vec!["127.0.0.1:0".parse::<SocketAddr>().expect("bind addr")],
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "shared-session-token".to_string(),
        heartbeat_timeout: Duration::from_secs(2),
        allow_private_targets: true,
    })
    .await
    .expect("spawn server");

    let bound_addr = server
        .snapshot()
        .await
        .bound_addrs
        .first()
        .cloned()
        .expect("bound addr");
    let parsed_addr = bound_addr.parse::<SocketAddr>().expect("socket addr");

    let client = spawn_client(ClientConfig {
        manifest_id: "manifest-1".to_string(),
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "shared-session-token".to_string(),
        route: TransportRoute {
            endpoint_ref: "node-lab-01".to_string(),
            dial_host: parsed_addr.ip().to_string(),
            dial_port: parsed_addr.port(),
            server_name: None,
            preference: 10,
            policy_tag: "primary".to_string(),
        },
        connect_timeout: Duration::from_secs(2),
        heartbeat_interval: Duration::from_millis(150),
        reconnect_delay: Duration::from_millis(100),
    });

    wait_until(
        || async {
            let snapshot = client.snapshot().await;
            snapshot.ready
        },
        Duration::from_secs(3),
    )
    .await;

    let _stalled_stream = client
        .open_stream(StreamTarget::new(
            flood_addr.ip().to_string(),
            flood_addr.port(),
        ))
        .await
        .expect("open stalled flood stream");

    tokio::time::sleep(Duration::from_millis(200)).await;

    let mut open_latencies_ms = Vec::new();
    let mut first_byte_latencies_ms = Vec::new();

    for _ in 0..20 {
        let open_started = std::time::Instant::now();
        let mut probe_stream = timeout(
            Duration::from_secs(1),
            client.open_stream(StreamTarget::new(
                echo_addr.ip().to_string(),
                echo_addr.port(),
            )),
        )
        .await
        .expect("probe open timeout")
        .expect("probe stream");
        open_latencies_ms.push(open_started.elapsed().as_millis());

        let writer = probe_stream.writer();
        let first_byte_started = std::time::Instant::now();
        writer
            .send(b"probe".to_vec())
            .await
            .expect("send probe payload");
        let echoed = timeout(Duration::from_secs(1), probe_stream.recv())
            .await
            .expect("probe recv timeout")
            .expect("probe recv");
        assert_eq!(echoed, b"probe".to_vec());
        first_byte_latencies_ms.push(first_byte_started.elapsed().as_millis());
        writer.close("probe-complete").await.expect("close probe");
        tokio::time::sleep(Duration::from_millis(15)).await;
    }

    open_latencies_ms.sort_unstable();
    first_byte_latencies_ms.sort_unstable();
    let p95_open_ms = percentile_ms(&open_latencies_ms, 95);
    let p95_first_byte_ms = percentile_ms(&first_byte_latencies_ms, 95);

    assert!(
        p95_open_ms <= 300,
        "p95 probe open too high while sibling receiver is stalled: {p95_open_ms} ms"
    );
    assert!(
        p95_first_byte_ms <= 450,
        "p95 probe first-byte too high while sibling receiver is stalled: {p95_first_byte_ms} ms"
    );

    let snapshot = client.snapshot().await;
    assert_eq!(snapshot.reconnect_attempts, 0);
    assert_eq!(snapshot.pending_open_streams, 0);
    assert!(snapshot.ready);

    eprintln!(
        "Helix stalled-sibling fairness: p95_open={}ms p95_first_byte={}ms",
        p95_open_ms, p95_first_byte_ms
    );

    shutdown_test_session_with_fixtures(&client, &server, &mut fixture_tasks).await;
}

#[tokio::test]
async fn server_keeps_probe_streams_responsive_while_downstream_bulk_flood_is_active() {
    let _test_guard = acquire_session_test_guard().await;
    let mut fixture_tasks = Vec::new();

    let source_listener = TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind source upstream");
    let source_addr = source_listener.local_addr().expect("source addr");
    fixture_tasks.push(tokio::spawn(async move {
        loop {
            let Ok((mut stream, _)) = source_listener.accept().await else {
                break;
            };
            tokio::spawn(async move {
                let payload = vec![0x61_u8; 16 * 1024];
                for _ in 0..256 {
                    if stream.write_all(&payload).await.is_err() {
                        return;
                    }
                }
                let _ = stream.shutdown().await;
            });
        }
    }));

    let echo_listener = TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind echo upstream");
    let echo_addr = echo_listener.local_addr().expect("echo addr");
    fixture_tasks.push(tokio::spawn(async move {
        loop {
            let Ok((mut stream, _)) = echo_listener.accept().await else {
                break;
            };
            tokio::spawn(async move {
                let mut buffer = [0_u8; 4096];
                loop {
                    match stream.read(&mut buffer).await {
                        Ok(0) => break,
                        Ok(read) => {
                            if stream.write_all(&buffer[..read]).await.is_err() {
                                break;
                            }
                        }
                        Err(_) => break,
                    }
                }
            });
        }
    }));

    let server = spawn_server(ServerConfig {
        bind_addrs: vec!["127.0.0.1:0".parse::<SocketAddr>().expect("bind addr")],
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "shared-session-token".to_string(),
        heartbeat_timeout: Duration::from_secs(2),
        allow_private_targets: true,
    })
    .await
    .expect("spawn server");

    let bound_addr = server
        .snapshot()
        .await
        .bound_addrs
        .first()
        .cloned()
        .expect("bound addr");
    let parsed_addr = bound_addr.parse::<SocketAddr>().expect("socket addr");

    let client = spawn_client(ClientConfig {
        manifest_id: "manifest-1".to_string(),
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "shared-session-token".to_string(),
        route: TransportRoute {
            endpoint_ref: "node-lab-01".to_string(),
            dial_host: parsed_addr.ip().to_string(),
            dial_port: parsed_addr.port(),
            server_name: None,
            preference: 10,
            policy_tag: "primary".to_string(),
        },
        connect_timeout: Duration::from_secs(2),
        heartbeat_interval: Duration::from_millis(150),
        reconnect_delay: Duration::from_millis(100),
    });

    wait_until(
        || async {
            let snapshot = client.snapshot().await;
            snapshot.ready
        },
        Duration::from_secs(3),
    )
    .await;

    let mut bulk_tasks = Vec::new();
    for _ in 0..4 {
        let mut stream = client
            .open_stream(StreamTarget::new(
                source_addr.ip().to_string(),
                source_addr.port(),
            ))
            .await
            .expect("open source stream");
        bulk_tasks.push(tokio::spawn(async move {
            while let Some(_data) = stream.recv().await {
                tokio::time::sleep(Duration::from_millis(2)).await;
            }
        }));
    }

    tokio::time::sleep(Duration::from_millis(25)).await;

    let mut open_latencies_ms = Vec::new();
    let mut first_byte_latencies_ms = Vec::new();
    for _ in 0..20 {
        let open_started = std::time::Instant::now();
        let mut probe_stream = timeout(
            Duration::from_secs(2),
            client.open_stream(StreamTarget::new(
                echo_addr.ip().to_string(),
                echo_addr.port(),
            )),
        )
        .await
        .expect("probe open timeout")
        .expect("probe stream");
        open_latencies_ms.push(open_started.elapsed().as_millis());

        let writer = probe_stream.writer();
        let first_byte_started = std::time::Instant::now();
        writer
            .send(b"probe".to_vec())
            .await
            .expect("send probe payload");
        let echoed = timeout(Duration::from_secs(2), probe_stream.recv())
            .await
            .expect("probe recv timeout")
            .expect("probe recv");
        assert_eq!(echoed, b"probe".to_vec());
        first_byte_latencies_ms.push(first_byte_started.elapsed().as_millis());
        writer.close("probe-complete").await.expect("close probe");
        tokio::time::sleep(Duration::from_millis(25)).await;
    }

    for task in bulk_tasks {
        task.await.expect("bulk task");
    }

    open_latencies_ms.sort_unstable();
    first_byte_latencies_ms.sort_unstable();
    let p95_open_ms = percentile_ms(&open_latencies_ms, 95);
    let p95_first_byte_ms = percentile_ms(&first_byte_latencies_ms, 95);
    let worst_open_ms = *open_latencies_ms.last().unwrap_or(&0);
    let worst_first_byte_ms = *first_byte_latencies_ms.last().unwrap_or(&0);

    assert!(
        p95_open_ms <= 300,
        "p95 probe open too high under downstream bulk flood: {p95_open_ms} ms"
    );
    assert!(
        p95_first_byte_ms <= 450,
        "p95 probe first-byte too high under downstream bulk flood: {p95_first_byte_ms} ms"
    );
    assert!(
        worst_open_ms <= 700 && worst_first_byte_ms <= 700,
        "worst-case downstream flood latency regressed too far: open={worst_open_ms} first-byte={worst_first_byte_ms}"
    );

    let snapshot = client.snapshot().await;
    assert_eq!(snapshot.reconnect_attempts, 0);
    assert_eq!(snapshot.pending_open_streams, 0);
    assert!(snapshot.ready);

    eprintln!(
        "Helix downstream-flood fairness: p95_open={}ms p95_first_byte={}ms worst_open={}ms worst_first_byte={}ms",
        p95_open_ms, p95_first_byte_ms, worst_open_ms, worst_first_byte_ms
    );

    shutdown_test_session_with_fixtures(&client, &server, &mut fixture_tasks).await;
}

#[tokio::test]
async fn server_drains_tail_data_before_stream_close_under_downstream_flood() {
    let _test_guard = acquire_session_test_guard().await;
    let mut fixture_tasks = Vec::new();

    let flood_listener = TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind flood upstream");
    let flood_addr = flood_listener.local_addr().expect("flood addr");
    fixture_tasks.push(tokio::spawn(async move {
        loop {
            let Ok((mut stream, _)) = flood_listener.accept().await else {
                break;
            };
            tokio::spawn(async move {
                let payload = vec![0x55_u8; 16 * 1024];
                for _ in 0..256 {
                    if stream.write_all(&payload).await.is_err() {
                        return;
                    }
                }
                let _ = stream.shutdown().await;
            });
        }
    }));

    let target_chunk = vec![0x7a_u8; 16 * 1024];
    let expected_chunks = 64_usize;
    let expected_total = target_chunk.len() * expected_chunks;
    let target_listener = TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind target upstream");
    let target_addr = target_listener.local_addr().expect("target addr");
    fixture_tasks.push(tokio::spawn(async move {
        loop {
            let Ok((mut stream, _)) = target_listener.accept().await else {
                break;
            };
            let target_chunk = target_chunk.clone();
            tokio::spawn(async move {
                for _ in 0..expected_chunks {
                    if stream.write_all(&target_chunk).await.is_err() {
                        return;
                    }
                }
                let _ = stream.shutdown().await;
            });
        }
    }));

    let server = spawn_server(ServerConfig {
        bind_addrs: vec!["127.0.0.1:0".parse::<SocketAddr>().expect("bind addr")],
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "shared-session-token".to_string(),
        heartbeat_timeout: Duration::from_secs(2),
        allow_private_targets: true,
    })
    .await
    .expect("spawn server");

    let bound_addr = server
        .snapshot()
        .await
        .bound_addrs
        .first()
        .cloned()
        .expect("bound addr");
    let parsed_addr = bound_addr.parse::<SocketAddr>().expect("socket addr");

    let client = spawn_client(ClientConfig {
        manifest_id: "manifest-1".to_string(),
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "shared-session-token".to_string(),
        route: TransportRoute {
            endpoint_ref: "node-lab-01".to_string(),
            dial_host: parsed_addr.ip().to_string(),
            dial_port: parsed_addr.port(),
            server_name: None,
            preference: 10,
            policy_tag: "primary".to_string(),
        },
        connect_timeout: Duration::from_secs(2),
        heartbeat_interval: Duration::from_millis(150),
        reconnect_delay: Duration::from_millis(100),
    });

    wait_until(
        || async {
            let snapshot = client.snapshot().await;
            snapshot.ready
        },
        Duration::from_secs(3),
    )
    .await;

    let mut flood_tasks = Vec::new();
    for _ in 0..3 {
        let mut stream = client
            .open_stream(StreamTarget::new(
                flood_addr.ip().to_string(),
                flood_addr.port(),
            ))
            .await
            .expect("open flood stream");
        flood_tasks.push(tokio::spawn(async move {
            while let Some(_data) = stream.recv().await {
                tokio::time::sleep(Duration::from_millis(2)).await;
            }
        }));
    }

    tokio::time::sleep(Duration::from_millis(25)).await;

    let mut target_stream = client
        .open_stream(StreamTarget::new(
            target_addr.ip().to_string(),
            target_addr.port(),
        ))
        .await
        .expect("open target stream");

    let mut received_total = 0_usize;
    loop {
        match timeout(Duration::from_secs(2), target_stream.recv()).await {
            Ok(Some(data)) => {
                received_total = received_total.saturating_add(data.len());
            }
            Ok(None) => break,
            Err(_) => panic!("timed out waiting for downstream tail payload under flood"),
        }
    }

    assert_eq!(
        received_total, expected_total,
        "server truncated downstream payload before stream close under flood"
    );

    for task in flood_tasks {
        task.await.expect("flood task");
    }

    shutdown_test_session_with_fixtures(&client, &server, &mut fixture_tasks).await;
}

#[tokio::test]
async fn client_keeps_probe_streams_responsive_while_many_bulk_streams_are_backpressured() {
    let _test_guard = acquire_session_test_guard().await;
    let mut fixture_tasks = Vec::new();

    let sink_listener = TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind sink upstream");
    let sink_addr = sink_listener.local_addr().expect("sink addr");
    fixture_tasks.push(tokio::spawn(async move {
        loop {
            let Ok((mut stream, _)) = sink_listener.accept().await else {
                break;
            };
            tokio::spawn(async move {
                let mut buffer = [0_u8; 16 * 1024];
                loop {
                    match stream.read(&mut buffer).await {
                        Ok(0) => break,
                        Ok(_) => {
                            tokio::time::sleep(Duration::from_millis(2)).await;
                        }
                        Err(_) => break,
                    }
                }
            });
        }
    }));

    let echo_listener = TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind echo upstream");
    let echo_addr = echo_listener.local_addr().expect("echo addr");
    fixture_tasks.push(tokio::spawn(async move {
        loop {
            let Ok((mut stream, _)) = echo_listener.accept().await else {
                break;
            };
            tokio::spawn(async move {
                let mut buffer = [0_u8; 4096];
                loop {
                    match stream.read(&mut buffer).await {
                        Ok(0) => break,
                        Ok(read) => {
                            if stream.write_all(&buffer[..read]).await.is_err() {
                                break;
                            }
                        }
                        Err(_) => break,
                    }
                }
            });
        }
    }));

    let server = spawn_server(ServerConfig {
        bind_addrs: vec!["127.0.0.1:0".parse::<SocketAddr>().expect("bind addr")],
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "shared-session-token".to_string(),
        heartbeat_timeout: Duration::from_secs(2),
        allow_private_targets: true,
    })
    .await
    .expect("spawn server");

    let bound_addr = server
        .snapshot()
        .await
        .bound_addrs
        .first()
        .cloned()
        .expect("bound addr");
    let parsed_addr = bound_addr.parse::<SocketAddr>().expect("socket addr");

    let client = spawn_client(ClientConfig {
        manifest_id: "manifest-1".to_string(),
        transport_profile_id: "ptp-lab-edge-v2".to_string(),
        profile_family: "edge-hybrid".to_string(),
        profile_version: 2,
        policy_version: 4,
        session_mode: "hybrid".to_string(),
        token: "shared-session-token".to_string(),
        route: TransportRoute {
            endpoint_ref: "node-lab-01".to_string(),
            dial_host: parsed_addr.ip().to_string(),
            dial_port: parsed_addr.port(),
            server_name: None,
            preference: 10,
            policy_tag: "primary".to_string(),
        },
        connect_timeout: Duration::from_secs(2),
        heartbeat_interval: Duration::from_millis(150),
        reconnect_delay: Duration::from_millis(100),
    });

    wait_until(
        || async {
            let snapshot = client.snapshot().await;
            snapshot.ready
        },
        Duration::from_secs(3),
    )
    .await;

    let bulk_payload = vec![0x42_u8; 64 * 1024];
    let mut bulk_tasks = Vec::new();
    for _ in 0..4 {
        let stream = client
            .open_stream(StreamTarget::new(
                sink_addr.ip().to_string(),
                sink_addr.port(),
            ))
            .await
            .expect("open bulk stream");
        let writer = stream.writer();
        let payload = bulk_payload.clone();
        bulk_tasks.push(tokio::spawn(async move {
            for _ in 0..64 {
                writer
                    .send(payload.clone())
                    .await
                    .expect("send bulk payload");
            }
            writer.close("bulk-complete").await.expect("close bulk");
        }));
    }

    tokio::time::sleep(Duration::from_millis(25)).await;

    let mut open_latencies_ms = Vec::new();
    let mut first_byte_latencies_ms = Vec::new();
    for _ in 0..20 {
        let open_started = std::time::Instant::now();
        let mut probe_stream = timeout(
            Duration::from_secs(2),
            client.open_stream(StreamTarget::new(
                echo_addr.ip().to_string(),
                echo_addr.port(),
            )),
        )
        .await
        .expect("probe open timeout")
        .expect("probe stream");
        open_latencies_ms.push(open_started.elapsed().as_millis());

        let writer = probe_stream.writer();
        let first_byte_started = std::time::Instant::now();
        writer
            .send(b"probe".to_vec())
            .await
            .expect("send probe payload");
        let echoed = timeout(Duration::from_secs(2), probe_stream.recv())
            .await
            .expect("probe recv timeout")
            .expect("probe recv");
        assert_eq!(echoed, b"probe".to_vec());
        first_byte_latencies_ms.push(first_byte_started.elapsed().as_millis());
        writer.close("probe-complete").await.expect("close probe");
        tokio::time::sleep(Duration::from_millis(25)).await;
    }

    for task in bulk_tasks {
        task.await.expect("bulk task");
    }

    open_latencies_ms.sort_unstable();
    first_byte_latencies_ms.sort_unstable();
    let p95_open_ms = percentile_ms(&open_latencies_ms, 95);
    let p95_first_byte_ms = percentile_ms(&first_byte_latencies_ms, 95);
    let worst_open_ms = *open_latencies_ms.last().unwrap_or(&0);
    let worst_first_byte_ms = *first_byte_latencies_ms.last().unwrap_or(&0);

    assert!(
        p95_open_ms <= 300,
        "p95 probe open too high under backpressured bulk streams: {p95_open_ms} ms"
    );
    assert!(
        p95_first_byte_ms <= 500,
        "p95 first-byte too high under backpressured bulk streams: {p95_first_byte_ms} ms"
    );
    assert!(
        worst_open_ms <= 700 && worst_first_byte_ms <= 700,
        "worst-case probe latency regressed too far: open={worst_open_ms} first-byte={worst_first_byte_ms}"
    );

    let snapshot = client.snapshot().await;
    assert_eq!(snapshot.reconnect_attempts, 0);
    assert_eq!(snapshot.pending_open_streams, 0);
    assert!(snapshot.ready);

    eprintln!(
        "Helix many-bulk-probe fairness: p95_open={}ms p95_first_byte={}ms worst_open={}ms worst_first_byte={}ms",
        p95_open_ms, p95_first_byte_ms, worst_open_ms, worst_first_byte_ms
    );

    shutdown_test_session_with_fixtures(&client, &server, &mut fixture_tasks).await;
}

async fn wait_until<F, Fut>(condition: F, timeout: Duration)
where
    F: Fn() -> Fut,
    Fut: std::future::Future<Output = bool>,
{
    let deadline = tokio::time::Instant::now() + timeout;
    loop {
        if condition().await {
            break;
        }

        assert!(
            tokio::time::Instant::now() < deadline,
            "condition was not satisfied before timeout"
        );

        tokio::time::sleep(Duration::from_millis(50)).await;
    }
}

fn percentile_ms(samples: &[u128], percentile: usize) -> u128 {
    if samples.is_empty() {
        return 0;
    }

    let rank = ((samples.len() - 1) * percentile) / 100;
    samples[rank]
}
