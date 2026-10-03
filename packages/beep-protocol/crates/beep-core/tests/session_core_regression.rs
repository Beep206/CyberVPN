//! Regression tests for session-core defects found during the TSPU hardening
//! review (stage 1 of the Beep refinement plan).
//!
//! Each test pins one defect. The first two are fixed by the per-direction
//! nonce change; the remaining `#[ignore]`d tests document defects scheduled
//! for the next stage-1 increments (flow-control replenishment and
//! per-direction rekey) and are expected to fail until then.

use beep_core::codec;
use beep_core::key_schedule::{derive_session_keys, SessionKeys};
use beep_core::mux::StreamFrame;
use beep_core::session_core::{IncomingAction, SessionCore};

fn keys() -> SessionKeys {
    derive_session_keys(&[0x11u8; 32], &[0x22u8; 32])
}

/// The two directions must not share a keystream.
///
/// Before the fix, `client.send` and `server.send` both started at sequence 0
/// with the same key and IV, so XOR-ing a client frame with a server frame of
/// equal length returned the XOR of the two plaintexts.
#[test]
fn directions_do_not_share_keystream() {
    let k = keys();
    let mut client = SessionCore::new(&k, true);
    let mut server = SessionCore::new(&k, false);

    let cs = client.open_stream();
    let ss = server.open_stream();
    let pa = b"client secret payload AAAAAAAAAA";
    let pb = b"server secret payload BBBBBBBBBB";

    let ca = client.seal_stream(cs, pa, false).unwrap();
    let cb = server.seal_stream(ss, pb, false).unwrap();
    let (fa, _) = codec::decode_frame(&ca.data).unwrap();
    let (fb, _) = codec::decode_frame(&cb.data).unwrap();

    let mut ea = Vec::new();
    StreamFrame {
        stream_id: cs.0,
        offset: 0,
        fin: false,
        data: pa.to_vec(),
    }
    .encode(&mut ea)
    .unwrap();
    let mut eb = Vec::new();
    StreamFrame {
        stream_id: ss.0,
        offset: 0,
        fin: false,
        data: pb.to_vec(),
    }
    .encode(&mut eb)
    .unwrap();
    assert_eq!(ea.len(), eb.len(), "test needs equal-length encoded frames");

    let n = ea.len();
    let xor_ct: Vec<u8> = fa.payload[..n]
        .iter()
        .zip(&fb.payload[..n])
        .map(|(x, y)| x ^ y)
        .collect();
    let xor_pt: Vec<u8> = ea.iter().zip(&eb).map(|(x, y)| x ^ y).collect();
    assert_ne!(xor_ct, xor_pt, "the two directions still share a keystream");
}

/// Both directions must interoperate end to end under the per-direction nonce.
#[test]
fn bidirectional_exchange_roundtrips() {
    let k = keys();
    let mut client = SessionCore::new(&k, true);
    let mut server = SessionCore::new(&k, false);

    let cs = client.open_stream();
    let up = client.seal_stream(cs, b"hello from client", false).unwrap();
    match server.process_incoming(&up.data).unwrap() {
        IncomingAction::StreamData { frame, .. } => assert_eq!(frame.data, b"hello from client"),
        other => panic!("expected StreamData, got {other:?}"),
    }

    let ssid = server.open_stream();
    let down = server
        .seal_stream(ssid, b"hello from server", false)
        .unwrap();
    match client.process_incoming(&down.data).unwrap() {
        IncomingAction::StreamData { frame, .. } => assert_eq!(frame.data, b"hello from server"),
        other => panic!("expected StreamData, got {other:?}"),
    }
}

/// A stream must carry far more than one default flow-control window.
///
/// The receiver replenishes `FLOW_CREDIT` as it consumes its window; the
/// sender applies those grants and keeps going. Before the fix the receiver
/// never granted credit, so the sender stalled after 64 KiB.
#[test]
fn stream_survives_beyond_default_window() {
    let k = keys();
    let mut client = SessionCore::new(&k, true);
    let mut server = SessionCore::new(&k, false);
    let sid = client.open_stream();

    let chunk = vec![7u8; 1024];
    let target = 4 * 1024 * 1024; // 64x the default window
    let mut sent = 0usize;
    while sent < target {
        let sealed = client
            .seal_stream(sid, &chunk, false)
            .expect("send credit must be replenished by the peer's grants");
        sent += chunk.len();

        server.process_incoming(&sealed.data).unwrap();
        // The receiver's grants flow back and top up the sender's credit.
        for grant in server.take_pending_tx() {
            client.process_incoming(&grant.data).unwrap();
        }
    }
    assert!(sent >= target);
}

/// A frame already in flight must survive a locally initiated rekey.
///
/// Initiating a rekey rotates only the send keys, so a frame the peer sent
/// under the previous epoch still decrypts under our unchanged receive keys.
#[test]
fn in_flight_frame_survives_local_rekey() {
    let k = keys();
    let mut client = SessionCore::new(&k, true);
    let mut server = SessionCore::new(&k, false);

    let ssid = server.open_stream();
    let in_flight = server
        .seal_stream(ssid, b"sent under epoch 0", false)
        .unwrap();

    // Client rekeys its send direction (sends KEY_UPDATE, rotates send keys).
    client.initiate_rekey().unwrap();
    client.complete_initiated_rekey().unwrap();

    // The peer's earlier frame still decrypts: our receive keys did not move.
    match client
        .process_incoming(&in_flight.data)
        .expect("a frame sent before the peer saw KEY_UPDATE must still decrypt")
    {
        IncomingAction::StreamData { frame, .. } => assert_eq!(frame.data, b"sent under epoch 0"),
        other => panic!("expected StreamData, got {other:?}"),
    }
}

/// After a full bidirectional rekey, traffic continues in both directions.
#[test]
fn bidirectional_rekey_then_traffic() {
    let k = keys();
    let mut client = SessionCore::new(&k, true);
    let mut server = SessionCore::new(&k, false);

    // Client rekeys its send direction and the server applies it on receive.
    let ku = client.initiate_rekey().unwrap();
    client.complete_initiated_rekey().unwrap();
    match server.process_incoming(&ku.data).unwrap() {
        IncomingAction::Rekeyed { epoch } => assert_eq!(epoch, 1),
        other => panic!("expected Rekeyed, got {other:?}"),
    }

    // Client -> server now rides the new send epoch.
    let cs = client.open_stream();
    let up = client
        .seal_stream(cs, b"after client rekey", false)
        .unwrap();
    match server.process_incoming(&up.data).unwrap() {
        IncomingAction::StreamData { frame, .. } => assert_eq!(frame.data, b"after client rekey"),
        other => panic!("expected StreamData, got {other:?}"),
    }

    // Server -> client still works on the untouched reverse direction.
    let ss = server.open_stream();
    let down = server.seal_stream(ss, b"reverse still ok", false).unwrap();
    match client.process_incoming(&down.data).unwrap() {
        IncomingAction::StreamData { frame, .. } => assert_eq!(frame.data, b"reverse still ok"),
        other => panic!("expected StreamData, got {other:?}"),
    }
}
