//! The node-side gate: only a request with the secret path and headers becomes
//! a tunnel; everything else gets a bare 404 and never reaches the session.

use beep_cover_wss::{accept_ws, client_ws_handshake, WsGate};
use beep_transport::CoverConn;
use bytes::Bytes;

const BINDING: [u8; 32] = [7u8; 32];
const PATH: &str = "/assets/chunk-4b7e91.js";

fn gate() -> WsGate {
    WsGate::new(
        PATH,
        &[("x-edge-token".to_string(), "k9Zq3vTt".to_string())],
    )
    .unwrap()
}

fn good_headers() -> Vec<(String, String)> {
    vec![("x-edge-token".to_string(), "k9Zq3vTt".to_string())]
}

/// Run a client handshake against the gate over an in-memory pipe.
async fn attempt(
    path: &str,
    headers: &[(String, String)],
) -> (
    Result<beep_cover_wss::WssCoverConn<tokio::io::DuplexStream>, beep_transport::TransportError>,
    Result<beep_cover_wss::WssCoverConn<tokio::io::DuplexStream>, beep_transport::TransportError>,
) {
    let (c, s) = tokio::io::duplex(64 * 1024);
    let gate = gate();
    let server = tokio::spawn(async move { accept_ws(s, &gate, BINDING).await });
    let client = client_ws_handshake(c, "site.example", path, headers, BINDING).await;
    (client, server.await.unwrap())
}

#[tokio::test]
async fn matching_path_and_header_become_a_tunnel() {
    let (client, server) = attempt(PATH, &good_headers()).await;
    let mut client = client.expect("client upgrade");
    let mut server = server.expect("server upgrade");

    client
        .send(Bytes::from_static(b"hello node"))
        .await
        .unwrap();
    assert_eq!(server.recv().await.unwrap().unwrap(), &b"hello node"[..]);
    server
        .send(Bytes::from_static(b"hello client"))
        .await
        .unwrap();
    assert_eq!(client.recv().await.unwrap().unwrap(), &b"hello client"[..]);
    assert_eq!(client.transport_binding(), BINDING);
}

#[tokio::test]
async fn wrong_path_is_refused_with_404() {
    let (client, server) = attempt("/other", &good_headers()).await;
    let err = client.err().expect("client must not get a tunnel");
    assert!(err.to_string().contains("404"), "got: {err}");
    assert!(server.is_err());
}

#[tokio::test]
async fn missing_secret_header_is_refused() {
    let (client, server) = attempt(PATH, &[]).await;
    let err = client.err().expect("client must not get a tunnel");
    assert!(err.to_string().contains("404"), "got: {err}");
    assert!(server.is_err());
}

#[tokio::test]
async fn wrong_secret_value_is_refused() {
    let (client, server) = attempt(
        PATH,
        &[("x-edge-token".to_string(), "k9Zq3vTT".to_string())],
    )
    .await;
    assert!(client.is_err());
    assert!(server.is_err());
}

#[tokio::test]
async fn secret_header_value_prefix_is_not_enough() {
    let (client, server) =
        attempt(PATH, &[("x-edge-token".to_string(), "k9Zq3v".to_string())]).await;
    assert!(client.is_err());
    assert!(server.is_err());
}

#[tokio::test]
async fn query_string_does_not_change_the_path_match() {
    let (client, server) = attempt(&format!("{PATH}?v=3"), &good_headers()).await;
    assert!(client.is_ok());
    assert!(server.is_ok());
}

#[tokio::test]
async fn open_gate_admits_any_path() {
    let (c, s) = tokio::io::duplex(64 * 1024);
    let server = tokio::spawn(async move { accept_ws(s, &WsGate::open(), BINDING).await });
    let client = client_ws_handshake(c, "site.example", "/anything", &[], BINDING).await;
    assert!(client.is_ok());
    assert!(server.await.unwrap().is_ok());
}
