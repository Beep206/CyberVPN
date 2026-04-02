use std::{
    collections::{HashMap, VecDeque},
    net::{IpAddr, SocketAddr},
    sync::Arc,
};

use tokio::{
    io::{AsyncRead, AsyncReadExt, AsyncWrite, AsyncWriteExt},
    net::{lookup_host, tcp::OwnedReadHalf, tcp::OwnedWriteHalf, TcpListener, TcpStream},
    sync::{mpsc, watch, Mutex, Notify, RwLock},
    task::{yield_now, AbortHandle},
    time::{timeout, Duration, Instant},
};
use uuid::Uuid;

use crate::{
    crypto::{
        client_proof, decrypt_frame, derive_session_key, encrypt_frame, random_nonce, server_proof,
        unix_timestamp_ms, Direction,
    },
    error::TransportError,
    model::{
        ControlFrame, HandshakeHello, HandshakeWelcome, ServerConfig, ServerSnapshot,
        PROTOCOL_MAGIC, PROTOCOL_VERSION,
    },
};

const CONTROL_FRAME_CHANNEL_CAPACITY: usize = 256;
const DATA_FRAME_CHANNEL_CAPACITY: usize = 16;
const STREAM_CHANNEL_CAPACITY: usize = 1024;
const STREAM_BUFFER_SIZE: usize = 8 * 1024;
const MAX_STREAM_FRAME_PAYLOAD: usize = 8 * 1024;
const CONTENDED_STREAM_FRAME_PAYLOAD: usize = 4 * 1024;
const HEAVILY_CONTENDED_STREAM_FRAME_PAYLOAD: usize = 2 * 1024;
const MAX_PENDING_INGRESS_BYTES: usize = 1024 * 1024;
const MAX_PENDING_EGRESS_BYTES: usize = 8 * 1024 * 1024;
const MAX_PENDING_EGRESS_BYTES_PER_STREAM: usize = 512 * 1024;
const WRITER_CONTROL_BURST_LIMIT: usize = 2;
const SESSION_RESUME_WINDOW_MULTIPLIER: u32 = 5;

type ServerStreamTx = mpsc::Sender<Vec<u8>>;

#[derive(Debug, Clone)]
struct ServerStreamHandle {
    outbound_tx: ServerStreamTx,
    bind_target: String,
    reader_abort: AbortHandle,
    writer_abort: AbortHandle,
}

type ServerStreamMap = Arc<Mutex<HashMap<u64, ServerStreamHandle>>>;

#[derive(Debug)]
enum ServerIngressAction {
    StreamData { stream_id: u64, data: Vec<u8> },
    CloseStream { stream_id: u64, reason: String },
}

#[derive(Debug)]
enum ServerEgressAction {
    StreamData { stream_id: u64, data: Vec<u8> },
    StreamClose { stream_id: u64, reason: String },
}

#[derive(Debug, Default)]
struct ServerIngressState {
    pending_data: HashMap<u64, VecDeque<Vec<u8>>>,
    pending_closes: HashMap<u64, String>,
    schedule: VecDeque<u64>,
    pending_bytes: usize,
}

#[derive(Debug, Default)]
struct ServerEgressState {
    pending_data: HashMap<u64, VecDeque<Vec<u8>>>,
    pending_bytes_by_stream: HashMap<u64, usize>,
    pending_closes: HashMap<u64, String>,
    schedule: VecDeque<u64>,
    pending_bytes: usize,
}

#[derive(Debug, Clone)]
struct ServerIngress {
    state: Arc<Mutex<ServerIngressState>>,
    notify: Arc<Notify>,
}

#[derive(Debug, Clone)]
struct ServerEgress {
    state: Arc<Mutex<ServerEgressState>>,
    notify: Arc<Notify>,
}

#[derive(Debug, Clone)]
struct ServerControl {
    state: Arc<Mutex<VecDeque<ControlFrame>>>,
    notify: Arc<Notify>,
}

#[derive(Debug, Clone)]
struct ResumableServerSession {
    session_id: String,
    streams: ServerStreamMap,
    control: ServerControl,
    ingress: ServerIngress,
    egress: ServerEgress,
    ingress_task_abort: AbortHandle,
    attached: bool,
    detached_at: Option<Instant>,
}

type SessionRegistry = Arc<Mutex<HashMap<String, ResumableServerSession>>>;

#[derive(Debug, Clone)]
pub struct ServerHandle {
    snapshot: Arc<RwLock<ServerSnapshot>>,
    shutdown_tx: watch::Sender<bool>,
}

impl ServerHandle {
    pub fn snapshot_handle(&self) -> Arc<RwLock<ServerSnapshot>> {
        self.snapshot.clone()
    }

    pub async fn snapshot(&self) -> ServerSnapshot {
        self.snapshot.read().await.clone()
    }

    pub async fn shutdown(&self) {
        let _ = self.shutdown_tx.send(true);
    }
}

pub async fn spawn_server(config: ServerConfig) -> Result<ServerHandle, TransportError> {
    if config.bind_addrs.is_empty() {
        return Err(TransportError::Protocol(
            "server config must include at least one bind address".to_string(),
        ));
    }

    let mut listeners = Vec::new();
    let mut bound_addrs = Vec::new();
    for bind_addr in &config.bind_addrs {
        let listener = TcpListener::bind(bind_addr).await?;
        bound_addrs.push(listener.local_addr()?.to_string());
        listeners.push(listener);
    }

    let snapshot = Arc::new(RwLock::new(ServerSnapshot {
        ready: true,
        bound_addrs,
        ..ServerSnapshot::default()
    }));
    let session_registry: SessionRegistry = Arc::new(Mutex::new(HashMap::new()));
    let (shutdown_tx, shutdown_rx) = watch::channel(false);

    for listener in listeners {
        tokio::spawn(run_accept_loop(
            listener,
            config.clone(),
            snapshot.clone(),
            session_registry.clone(),
            shutdown_rx.clone(),
        ));
    }

    Ok(ServerHandle {
        snapshot,
        shutdown_tx,
    })
}

fn session_resume_window(config: &ServerConfig) -> Duration {
    config
        .heartbeat_timeout
        .checked_mul(SESSION_RESUME_WINDOW_MULTIPLIER)
        .unwrap_or(config.heartbeat_timeout)
}

async fn prune_expired_detached_sessions(
    registry: &SessionRegistry,
    snapshot: &Arc<RwLock<ServerSnapshot>>,
    resume_window: Duration,
) {
    let expired_sessions = {
        let now = Instant::now();
        let mut state = registry.lock().await;
        let expired_ids = state
            .iter()
            .filter_map(|(session_id, session)| {
                session
                    .detached_at
                    .filter(|detached_at| !session.attached && now.duration_since(*detached_at) > resume_window)
                    .map(|_| session_id.clone())
            })
            .collect::<Vec<_>>();

        expired_ids
            .into_iter()
            .filter_map(|session_id| state.remove(&session_id))
            .collect::<Vec<_>>()
    };

    for session in expired_sessions {
        session.ingress_task_abort.abort();
        cleanup_streams(snapshot, &session.streams).await;
        let mut guard = snapshot.write().await;
        guard.active_sessions = guard.active_sessions.saturating_sub(1);
    }
}

fn enable_low_latency_mode(stream: &TcpStream) {
    let _ = stream.set_nodelay(true);
}

fn schedule_server_ingress_stream(state: &mut ServerIngressState, stream_id: u64) {
    if !state
        .schedule
        .iter()
        .any(|scheduled| *scheduled == stream_id)
    {
        state.schedule.push_back(stream_id);
    }
}

fn contended_stream_frame_payload(stream_count: usize) -> usize {
    if stream_count >= 6 {
        HEAVILY_CONTENDED_STREAM_FRAME_PAYLOAD
    } else if stream_count >= 3 {
        CONTENDED_STREAM_FRAME_PAYLOAD
    } else {
        MAX_STREAM_FRAME_PAYLOAD
    }
}

fn schedule_server_ingress_stream_front(state: &mut ServerIngressState, stream_id: u64) {
    if !state
        .schedule
        .iter()
        .any(|scheduled| *scheduled == stream_id)
    {
        state.schedule.push_front(stream_id);
    }
}

async fn enqueue_server_stream_data(
    stream_id: u64,
    data: Vec<u8>,
    ingress: &ServerIngress,
) -> usize {
    let mut state = ingress.state.lock().await;
    let is_new_stream = !state.pending_data.contains_key(&stream_id);
    state.pending_bytes = state.pending_bytes.saturating_add(data.len());
    state
        .pending_data
        .entry(stream_id)
        .or_default()
        .push_back(data);
    if is_new_stream {
        schedule_server_ingress_stream_front(&mut state, stream_id);
    } else {
        schedule_server_ingress_stream(&mut state, stream_id);
    }
    state.pending_bytes
}

async fn enqueue_server_stream_close(stream_id: u64, reason: String, ingress: &ServerIngress) {
    let mut state = ingress.state.lock().await;
    state.pending_closes.insert(stream_id, reason);
    schedule_server_ingress_stream(&mut state, stream_id);
}

async fn requeue_server_stream_data(stream_id: u64, data: Vec<u8>, ingress: &ServerIngress) {
    let mut state = ingress.state.lock().await;
    state.pending_bytes = state.pending_bytes.saturating_add(data.len());
    state
        .pending_data
        .entry(stream_id)
        .or_default()
        .push_front(data);
    schedule_server_ingress_stream(&mut state, stream_id);
}

async fn has_pending_server_ingress(ingress: &ServerIngress) -> bool {
    !ingress.state.lock().await.schedule.is_empty()
}

async fn dequeue_server_ingress_action(ingress: &ServerIngress) -> Option<ServerIngressAction> {
    let mut state = ingress.state.lock().await;

    while let Some(stream_id) = state.schedule.pop_front() {
        let mut drained_bytes = 0_usize;
        let mut should_remove = false;
        let data = if let Some(queue) = state.pending_data.get_mut(&stream_id) {
            let next = queue.pop_front();
            if let Some(chunk) = &next {
                drained_bytes = chunk.len();
            }
            if queue.is_empty() {
                should_remove = true;
            }
            next
        } else {
            None
        };

        if drained_bytes > 0 {
            state.pending_bytes = state.pending_bytes.saturating_sub(drained_bytes);
        }

        if should_remove {
            state.pending_data.remove(&stream_id);
        }

        if let Some(data) = data {
            if state.pending_data.contains_key(&stream_id)
                || state.pending_closes.contains_key(&stream_id)
            {
                schedule_server_ingress_stream(&mut state, stream_id);
            }
            return Some(ServerIngressAction::StreamData { stream_id, data });
        }

        if let Some(reason) = state.pending_closes.remove(&stream_id) {
            return Some(ServerIngressAction::CloseStream { stream_id, reason });
        }
    }

    None
}

async fn wait_for_server_ingress_capacity(ingress: &ServerIngress) {
    loop {
        let notified = {
            let state = ingress.state.lock().await;
            if state.pending_bytes <= MAX_PENDING_INGRESS_BYTES {
                return;
            }
            ingress.notify.notified()
        };

        notified.await;
    }
}

async fn enqueue_server_control_frame(frame: ControlFrame, control: &ServerControl) {
    let mut state = control.state.lock().await;
    state.push_back(frame);
}

async fn requeue_server_control_frame(frame: ControlFrame, control: &ServerControl) {
    let mut state = control.state.lock().await;
    state.push_front(frame);
}

async fn has_pending_server_control(control: &ServerControl) -> bool {
    !control.state.lock().await.is_empty()
}

async fn dequeue_server_control_frame(control: &ServerControl) -> Option<ControlFrame> {
    control.state.lock().await.pop_front()
}

fn schedule_server_egress_stream(state: &mut ServerEgressState, stream_id: u64) {
    if !state
        .schedule
        .iter()
        .any(|scheduled| *scheduled == stream_id)
    {
        state.schedule.push_back(stream_id);
    }
}

fn schedule_server_egress_stream_front(state: &mut ServerEgressState, stream_id: u64) {
    if !state
        .schedule
        .iter()
        .any(|scheduled| *scheduled == stream_id)
    {
        state.schedule.push_front(stream_id);
    }
}

async fn enqueue_server_egress_data(
    stream_id: u64,
    data: Vec<u8>,
    egress: &ServerEgress,
) -> (usize, usize) {
    let mut state = egress.state.lock().await;
    let is_new_stream = !state.pending_data.contains_key(&stream_id);
    let stream_pending_bytes = state
        .pending_bytes_by_stream
        .get(&stream_id)
        .copied()
        .unwrap_or(0);
    state.pending_bytes = state.pending_bytes.saturating_add(data.len());
    state
        .pending_bytes_by_stream
        .insert(stream_id, stream_pending_bytes.saturating_add(data.len()));
    state
        .pending_data
        .entry(stream_id)
        .or_default()
        .push_back(data);
    if is_new_stream {
        schedule_server_egress_stream_front(&mut state, stream_id);
    } else {
        schedule_server_egress_stream(&mut state, stream_id);
    }
    (
        state.pending_bytes,
        state
            .pending_bytes_by_stream
            .get(&stream_id)
            .copied()
            .unwrap_or(0),
    )
}

async fn enqueue_server_egress_close(stream_id: u64, reason: String, egress: &ServerEgress) {
    let mut state = egress.state.lock().await;
    state.pending_closes.insert(stream_id, reason);
    schedule_server_egress_stream(&mut state, stream_id);
}

async fn requeue_server_egress_data(stream_id: u64, data: Vec<u8>, egress: &ServerEgress) {
    let mut state = egress.state.lock().await;
    let stream_pending_bytes = state
        .pending_bytes_by_stream
        .get(&stream_id)
        .copied()
        .unwrap_or(0);
    state.pending_bytes = state.pending_bytes.saturating_add(data.len());
    state
        .pending_bytes_by_stream
        .insert(stream_id, stream_pending_bytes.saturating_add(data.len()));
    state
        .pending_data
        .entry(stream_id)
        .or_default()
        .push_front(data);
    schedule_server_egress_stream(&mut state, stream_id);
}

async fn has_pending_server_egress(egress: &ServerEgress) -> bool {
    !egress.state.lock().await.schedule.is_empty()
}

async fn dequeue_server_egress_action(egress: &ServerEgress) -> Option<ServerEgressAction> {
    let mut state = egress.state.lock().await;

    while let Some(stream_id) = state.schedule.pop_front() {
        let mut drained_bytes = 0_usize;
        let mut should_remove = false;
        let data = if let Some(queue) = state.pending_data.get_mut(&stream_id) {
            let next = queue.pop_front();
            if let Some(chunk) = &next {
                drained_bytes = chunk.len();
            }
            if queue.is_empty() {
                should_remove = true;
            }
            next
        } else {
            None
        };

        if drained_bytes > 0 {
            state.pending_bytes = state.pending_bytes.saturating_sub(drained_bytes);
            let mut remove_stream_bytes = false;
            if let Some(stream_pending_bytes) = state.pending_bytes_by_stream.get_mut(&stream_id) {
                *stream_pending_bytes = stream_pending_bytes.saturating_sub(drained_bytes);
                remove_stream_bytes = *stream_pending_bytes == 0;
            }
            if remove_stream_bytes {
                state.pending_bytes_by_stream.remove(&stream_id);
            }
        }

        if should_remove {
            state.pending_data.remove(&stream_id);
        }

        if let Some(mut data) = data {
            let limit = contended_stream_frame_payload(state.schedule.len().saturating_add(1));
            if data.len() > limit {
                let remainder = data.split_off(limit);
                let remainder_len = remainder.len();
                state.pending_bytes = state.pending_bytes.saturating_add(remainder_len);
                let stream_pending_bytes = state
                    .pending_bytes_by_stream
                    .get(&stream_id)
                    .copied()
                    .unwrap_or(0);
                state.pending_bytes_by_stream.insert(
                    stream_id,
                    stream_pending_bytes.saturating_add(remainder_len),
                );
                state
                    .pending_data
                    .entry(stream_id)
                    .or_default()
                    .push_front(remainder);
            }
            if state.pending_data.contains_key(&stream_id)
                || state.pending_closes.contains_key(&stream_id)
            {
                schedule_server_egress_stream(&mut state, stream_id);
            }
            return Some(ServerEgressAction::StreamData { stream_id, data });
        }

        if let Some(reason) = state.pending_closes.remove(&stream_id) {
            state.pending_bytes_by_stream.remove(&stream_id);
            return Some(ServerEgressAction::StreamClose { stream_id, reason });
        }
    }

    None
}

async fn wait_for_server_egress_capacity(egress: &ServerEgress) {
    loop {
        let notified = {
            let state = egress.state.lock().await;
            if state.pending_bytes <= MAX_PENDING_EGRESS_BYTES {
                return;
            }
            egress.notify.notified()
        };

        notified.await;
    }
}

async fn wait_for_server_egress_stream_capacity(stream_id: u64, egress: &ServerEgress) {
    loop {
        let notified = {
            let state = egress.state.lock().await;
            let stream_pending_bytes = state
                .pending_bytes_by_stream
                .get(&stream_id)
                .copied()
                .unwrap_or(0);
            if stream_pending_bytes <= MAX_PENDING_EGRESS_BYTES_PER_STREAM {
                return;
            }
            egress.notify.notified()
        };

        notified.await;
    }
}

async fn open_or_resume_server_session(
    config: &ServerConfig,
    hello: &HandshakeHello,
    session_registry: &SessionRegistry,
    snapshot: &Arc<RwLock<ServerSnapshot>>,
) -> ResumableServerSession {
    let resume_window = session_resume_window(config);
    prune_expired_detached_sessions(session_registry, snapshot, resume_window).await;

    let mut registry = session_registry.lock().await;
    if let Some(resume_session_id) = &hello.resume_session_id {
        if let Some(session) = registry.get_mut(resume_session_id) {
            if !session.attached {
                session.attached = true;
                session.detached_at = None;
                return session.clone();
            }
        }
    }

    let streams = Arc::new(Mutex::new(HashMap::<u64, ServerStreamHandle>::new()));
    let control = ServerControl {
        state: Arc::new(Mutex::new(VecDeque::new())),
        notify: Arc::new(Notify::new()),
    };
    let ingress = ServerIngress {
        state: Arc::new(Mutex::new(ServerIngressState::default())),
        notify: Arc::new(Notify::new()),
    };
    let egress = ServerEgress {
        state: Arc::new(Mutex::new(ServerEgressState::default())),
        notify: Arc::new(Notify::new()),
    };
    let ingress_task_abort = tokio::spawn(run_server_ingress_scheduler(
        ingress.clone(),
        egress.clone(),
        snapshot.clone(),
        streams.clone(),
    ))
    .abort_handle();

    let session = ResumableServerSession {
        session_id: Uuid::new_v4().to_string(),
        streams,
        control,
        ingress,
        egress,
        ingress_task_abort,
        attached: true,
        detached_at: None,
    };
    registry.insert(session.session_id.clone(), session.clone());
    session
}

async fn detach_or_cleanup_server_session(
    session_result: &Result<(), TransportError>,
    session: &ResumableServerSession,
    session_registry: &SessionRegistry,
    snapshot: &Arc<RwLock<ServerSnapshot>>,
) {
    let should_cleanup = session_result.is_ok()
        || matches!(
            session_result,
            Err(
                TransportError::Protocol(_)
                    | TransportError::Crypto(_)
                    | TransportError::Json(_)
                    | TransportError::Codec(_)
                    | TransportError::ChannelClosed(_)
            )
        );

    if should_cleanup {
        {
            let mut registry = session_registry.lock().await;
            registry.remove(&session.session_id);
        }
        session.ingress_task_abort.abort();
        cleanup_streams(snapshot, &session.streams).await;
        let mut guard = snapshot.write().await;
        guard.active_sessions = guard.active_sessions.saturating_sub(1);
        return;
    }

    let mut registry = session_registry.lock().await;
    if let Some(existing) = registry.get_mut(&session.session_id) {
        existing.attached = false;
        existing.detached_at = Some(Instant::now());
    }
}

async fn run_accept_loop(
    listener: TcpListener,
    config: ServerConfig,
    snapshot: Arc<RwLock<ServerSnapshot>>,
    session_registry: SessionRegistry,
    mut shutdown_rx: watch::Receiver<bool>,
) {
    loop {
        tokio::select! {
            changed = shutdown_rx.changed() => {
                if changed.is_ok() && *shutdown_rx.borrow() {
                    break;
                }
            }
            accept_result = listener.accept() => {
                match accept_result {
                    Ok((stream, _)) => {
                        enable_low_latency_mode(&stream);
                        let config = config.clone();
                        let snapshot = snapshot.clone();
                        let session_registry = session_registry.clone();
                        tokio::spawn(async move {
                            if let Err(error) = handle_connection(
                                stream,
                                config,
                                snapshot.clone(),
                                session_registry,
                            )
                            .await
                            {
                                let mut guard = snapshot.write().await;
                                guard.failed_handshakes = guard.failed_handshakes.saturating_add(1);
                                guard.last_error = Some(error.to_string());
                            }
                        });
                    }
                    Err(error) => {
                        let mut guard = snapshot.write().await;
                        guard.last_error = Some(error.to_string());
                    }
                }
            }
        }
    }
}

async fn handle_connection(
    mut stream: TcpStream,
    config: ServerConfig,
    snapshot: Arc<RwLock<ServerSnapshot>>,
    session_registry: SessionRegistry,
) -> Result<(), TransportError> {
    let hello = timeout(
        config.heartbeat_timeout,
        read_json_frame::<HandshakeHello, _>(&mut stream),
    )
    .await
    .map_err(|_| TransportError::Timeout("client handshake hello timed out".to_string()))??;

    verify_hello(&config, &hello)?;
    let expected_client_proof = client_proof(&config.token, &hello)?;
    if hello.proof != expected_client_proof {
        return Err(TransportError::Protocol(
            "client proof validation failed".to_string(),
        ));
    }

    let session = open_or_resume_server_session(&config, &hello, &session_registry, &snapshot).await;
    let resumed = hello
        .resume_session_id
        .as_ref()
        .map(|session_id| session_id == &session.session_id)
        .unwrap_or(false);

    let mut welcome = HandshakeWelcome {
        magic: PROTOCOL_MAGIC.to_string(),
        accepted: true,
        session_id: session.session_id.clone(),
        resumed,
        transport_profile_id: config.transport_profile_id.clone(),
        server_nonce: random_nonce(),
        heartbeat_interval_ms: u64::try_from(config.heartbeat_timeout.as_millis())
            .unwrap_or(u64::MAX),
        proof: [0_u8; 32],
        error: None,
    };
    welcome.proof = server_proof(&config.token, &welcome, &hello)?;
    write_json_frame(&mut stream, &welcome).await?;

    let session_key = derive_session_key(
        &config.token,
        &welcome.session_id,
        &config.transport_profile_id,
        &hello.client_nonce,
        &welcome.server_nonce,
    )?;

    let (reader, writer) = stream.into_split();
    let (control_frame_tx, control_frame_rx) = mpsc::channel(CONTROL_FRAME_CHANNEL_CAPACITY);
    let (data_frame_tx, data_frame_rx) = mpsc::channel(DATA_FRAME_CHANNEL_CAPACITY);
    let streams = session.streams.clone();
    let control = session.control.clone();
    let ingress = session.ingress.clone();
    let egress = session.egress.clone();

    {
        let active_streams = u64::try_from(streams.lock().await.len()).unwrap_or(u64::MAX);
        let mut guard = snapshot.write().await;
        guard.successful_handshakes = guard.successful_handshakes.saturating_add(1);
        if !resumed {
            guard.active_sessions = guard.active_sessions.saturating_add(1);
        }
        guard.active_streams = active_streams;
        guard.last_error = None;
    }

    let writer_task = tokio::spawn(run_frame_writer(
        writer,
        session_key,
        control_frame_rx,
        data_frame_rx,
        snapshot.clone(),
    ));
    let control_task = tokio::spawn(run_server_control_scheduler(
        control.clone(),
        control_frame_tx.clone(),
    ));
    let egress_task = tokio::spawn(run_server_egress_scheduler(
        egress.clone(),
        data_frame_tx.clone(),
    ));

    let session_result = run_server_session(
        reader,
        session_key,
        control,
        ingress,
        egress,
        config,
        snapshot.clone(),
        streams.clone(),
    )
    .await;

    writer_task.abort();
    control_task.abort();
    egress_task.abort();
    detach_or_cleanup_server_session(&session_result, &session, &session_registry, &snapshot).await;

    snapshot.write().await.active_streams = u64::try_from(streams.lock().await.len()).unwrap_or(u64::MAX);

    if let Err(error) = session_result {
        snapshot.write().await.last_error = Some(error.to_string());
    }

    Ok(())
}

#[allow(clippy::too_many_arguments)]
async fn run_server_session(
    mut reader: OwnedReadHalf,
    session_key: [u8; 32],
    control: ServerControl,
    ingress: ServerIngress,
    egress: ServerEgress,
    config: ServerConfig,
    snapshot: Arc<RwLock<ServerSnapshot>>,
    streams: ServerStreamMap,
) -> Result<(), TransportError> {
    let read_timeout = config.heartbeat_timeout;
    let mut incoming_seq = 0_u64;

    loop {
        let frame = timeout(
            read_timeout,
            read_encrypted_frame(
                &mut reader,
                &session_key,
                Direction::ClientToServer,
                &mut incoming_seq,
            ),
        )
        .await
        .map_err(|_| TransportError::Timeout("client frame timed out".to_string()))??;

        let data_len = match &frame {
            ControlFrame::StreamData { data, .. } => u64::try_from(data.len()).unwrap_or(u64::MAX),
            _ => 0,
        };
        {
            let mut guard = snapshot.write().await;
            guard.frames_in = guard.frames_in.saturating_add(1);
            guard.bytes_in = guard.bytes_in.saturating_add(data_len);
        }

        match frame {
            ControlFrame::Ping { sent_at_ms } => {
                enqueue_server_control_frame(
                    ControlFrame::Pong {
                        sent_at_ms,
                        server_timestamp_ms: unix_timestamp_ms(),
                    },
                    &control,
                )
                .await;
                control.notify.notify_one();
            }
            ControlFrame::StreamOpen {
                stream_id,
                target_host,
                target_port,
            } => {
                let config = config.clone();
                let control = control.clone();
                let egress = egress.clone();
                let snapshot = snapshot.clone();
                let streams = streams.clone();
                tokio::spawn(async move {
                    if let Err(error) = open_server_stream(
                        stream_id,
                        target_host,
                        target_port,
                        &config,
                        &control,
                        &egress,
                        &snapshot,
                        &streams,
                    )
                    .await
                    {
                        let mut guard = snapshot.write().await;
                        guard.last_error = Some(error.to_string());
                    }
                });
            }
            ControlFrame::StreamData { stream_id, data } => {
                let stream_known = {
                    let state = streams.lock().await;
                    state.contains_key(&stream_id)
                };

                if stream_known {
                    if enqueue_server_stream_data(stream_id, data, &ingress).await
                        > MAX_PENDING_INGRESS_BYTES
                    {
                        wait_for_server_ingress_capacity(&ingress).await;
                    }
                    ingress.notify.notify_one();
                } else {
                    enqueue_server_control_frame(
                        ControlFrame::StreamClose {
                            stream_id,
                            reason: "unknown stream".to_string(),
                        },
                        &control,
                    )
                    .await;
                    control.notify.notify_one();
                }
            }
            ControlFrame::StreamClose { stream_id, reason } => {
                enqueue_server_stream_close(stream_id, reason, &ingress).await;
                ingress.notify.notify_one();
            }
            ControlFrame::Close { .. } => break,
            ControlFrame::Pong { .. } => {
                return Err(TransportError::Protocol(
                    "unexpected pong received by server".to_string(),
                ));
            }
            ControlFrame::StreamOpened { .. } => {
                return Err(TransportError::Protocol(
                    "unexpected stream_opened received by server".to_string(),
                ));
            }
        }
    }

    Ok(())
}
async fn run_server_ingress_scheduler(
    ingress: ServerIngress,
    egress: ServerEgress,
    snapshot: Arc<RwLock<ServerSnapshot>>,
    streams: ServerStreamMap,
) -> Result<(), TransportError> {
    let mut has_pending_ingress = has_pending_server_ingress(&ingress).await;

    loop {
        if !has_pending_ingress {
            ingress.notify.notified().await;
            has_pending_ingress = has_pending_server_ingress(&ingress).await;
            continue;
        }

        let Some(action) = dequeue_server_ingress_action(&ingress).await else {
            has_pending_ingress = false;
            continue;
        };

        let progressed = match action {
            ServerIngressAction::StreamData { stream_id, data } => {
                let outbound = {
                    let state = streams.lock().await;
                    state.get(&stream_id).cloned()
                };

                if let Some(outbound) = outbound {
                    match outbound.outbound_tx.try_send(data) {
                        Ok(()) => {
                            ingress.notify.notify_waiters();
                            true
                        }
                        Err(mpsc::error::TrySendError::Full(data)) => {
                            requeue_server_stream_data(stream_id, data, &ingress).await;
                            false
                        }
                        Err(mpsc::error::TrySendError::Closed(_)) => {
                            close_server_stream(
                                stream_id,
                                "upstream writer closed".to_string(),
                                &egress,
                                &snapshot,
                                &streams,
                            )
                            .await?;
                            ingress.notify.notify_waiters();
                            true
                        }
                    }
                } else {
                    ingress.notify.notify_waiters();
                    true
                }
            }
            ServerIngressAction::CloseStream { stream_id, reason } => {
                close_server_stream(stream_id, reason, &egress, &snapshot, &streams).await?;
                ingress.notify.notify_waiters();
                true
            }
        };

        has_pending_ingress = has_pending_server_ingress(&ingress).await;
        if !progressed && has_pending_ingress {
            yield_now().await;
        }
    }
}

async fn run_server_control_scheduler(
    control: ServerControl,
    control_frame_tx: mpsc::Sender<ControlFrame>,
) -> Result<(), TransportError> {
    let mut has_pending_control = has_pending_server_control(&control).await;

    loop {
        if !has_pending_control {
            control.notify.notified().await;
            has_pending_control = has_pending_server_control(&control).await;
            continue;
        }

        let Some(frame) = dequeue_server_control_frame(&control).await else {
            has_pending_control = false;
            continue;
        };

        match control_frame_tx.try_send(frame) {
            Ok(()) => {}
            Err(mpsc::error::TrySendError::Full(frame)) => {
                requeue_server_control_frame(frame, &control).await;
                yield_now().await;
            }
            Err(mpsc::error::TrySendError::Closed(_)) => {
                return Err(TransportError::ChannelClosed("server control frame queue"));
            }
        }

        has_pending_control = has_pending_server_control(&control).await;
    }
}

async fn run_server_egress_scheduler(
    egress: ServerEgress,
    data_frame_tx: mpsc::Sender<ControlFrame>,
) -> Result<(), TransportError> {
    let mut has_pending_egress = has_pending_server_egress(&egress).await;

    loop {
        if !has_pending_egress {
            egress.notify.notified().await;
            has_pending_egress = has_pending_server_egress(&egress).await;
            continue;
        }

        let Some(action) = dequeue_server_egress_action(&egress).await else {
            has_pending_egress = false;
            continue;
        };

        let progressed = match action {
            ServerEgressAction::StreamData { stream_id, data } => {
                match data_frame_tx.try_send(ControlFrame::StreamData { stream_id, data }) {
                    Ok(()) => {
                        egress.notify.notify_waiters();
                        true
                    }
                    Err(mpsc::error::TrySendError::Full(ControlFrame::StreamData {
                        stream_id,
                        data,
                    })) => {
                        requeue_server_egress_data(stream_id, data, &egress).await;
                        false
                    }
                    Err(mpsc::error::TrySendError::Closed(_)) => {
                        return Err(TransportError::ChannelClosed("server data frame queue"));
                    }
                    Err(mpsc::error::TrySendError::Full(_)) => false,
                }
            }
            ServerEgressAction::StreamClose { stream_id, reason } => {
                match data_frame_tx.try_send(ControlFrame::StreamClose { stream_id, reason }) {
                    Ok(()) => {
                        egress.notify.notify_waiters();
                        true
                    }
                    Err(mpsc::error::TrySendError::Full(ControlFrame::StreamClose {
                        stream_id,
                        reason,
                    })) => {
                        enqueue_server_egress_close(stream_id, reason, &egress).await;
                        false
                    }
                    Err(mpsc::error::TrySendError::Closed(_)) => {
                        return Err(TransportError::ChannelClosed("server stream close"));
                    }
                    Err(mpsc::error::TrySendError::Full(_)) => false,
                }
            }
        };

        has_pending_egress = has_pending_server_egress(&egress).await;
        if !progressed && has_pending_egress {
            yield_now().await;
        }
    }
}

#[allow(clippy::too_many_arguments)]
async fn open_server_stream(
    stream_id: u64,
    target_host: String,
    target_port: u16,
    config: &ServerConfig,
    control: &ServerControl,
    egress: &ServerEgress,
    snapshot: &Arc<RwLock<ServerSnapshot>>,
    streams: &ServerStreamMap,
) -> Result<(), TransportError> {
    if let Some(bind_target) = {
        let state = streams.lock().await;
        state.get(&stream_id).map(|stream| stream.bind_target.clone())
    } {
        enqueue_server_control_frame(
            ControlFrame::StreamOpened {
                stream_id,
                bind_target,
            },
            control,
        )
        .await;
        control.notify.notify_one();
        return Ok(());
    }

    let target_addr =
        match resolve_target_addr(&target_host, target_port, config.allow_private_targets).await {
            Ok(addr) => addr,
            Err(error) => {
                let mut guard = snapshot.write().await;
                guard.rejected_targets = guard.rejected_targets.saturating_add(1);
                enqueue_server_control_frame(
                    ControlFrame::StreamClose {
                        stream_id,
                        reason: error.to_string(),
                    },
                    control,
                )
                .await;
                control.notify.notify_one();
                return Ok(());
            }
        };

    let upstream = match timeout(config.heartbeat_timeout, TcpStream::connect(target_addr)).await {
        Ok(Ok(stream)) => {
            enable_low_latency_mode(&stream);
            stream
        }
        Ok(Err(error)) => {
            enqueue_server_control_frame(
                ControlFrame::StreamClose {
                    stream_id,
                    reason: format!("upstream connect failed: {error}"),
                },
                control,
            )
            .await;
            control.notify.notify_one();
            return Ok(());
        }
        Err(_) => {
            enqueue_server_control_frame(
                ControlFrame::StreamClose {
                    stream_id,
                    reason: format!("upstream connect timeout: {target_addr}"),
                },
                control,
            )
            .await;
            control.notify.notify_one();
            return Ok(());
        }
    };

    let (upstream_reader, upstream_writer) = upstream.into_split();
    let (upstream_tx, upstream_rx) = mpsc::channel(STREAM_CHANNEL_CAPACITY);
    let bind_target = target_addr.to_string();
    let reader_task = tokio::spawn(run_upstream_reader(
        stream_id,
        upstream_reader,
        egress.clone(),
        snapshot.clone(),
        streams.clone(),
    ));
    let writer_task = tokio::spawn(run_upstream_writer(
        stream_id,
        upstream_writer,
        upstream_rx,
        egress.clone(),
        snapshot.clone(),
        streams.clone(),
    ));

    {
        let mut state = streams.lock().await;
        state.insert(
            stream_id,
            ServerStreamHandle {
                outbound_tx: upstream_tx,
                bind_target: bind_target.clone(),
                reader_abort: reader_task.abort_handle(),
                writer_abort: writer_task.abort_handle(),
            },
        );
        snapshot.write().await.active_streams = u64::try_from(state.len()).unwrap_or(u64::MAX);
    }

    enqueue_server_control_frame(
        ControlFrame::StreamOpened {
            stream_id,
            bind_target,
        },
        control,
    )
    .await;
    control.notify.notify_one();

    Ok(())
}
async fn run_upstream_reader(
    stream_id: u64,
    mut reader: OwnedReadHalf,
    egress: ServerEgress,
    snapshot: Arc<RwLock<ServerSnapshot>>,
    streams: ServerStreamMap,
) {
    let mut buffer = vec![0_u8; STREAM_BUFFER_SIZE];
    loop {
        match reader.read(&mut buffer).await {
            Ok(0) => {
                let _ = close_server_stream(
                    stream_id,
                    "upstream eof".to_string(),
                    &egress,
                    &snapshot,
                    &streams,
                )
                .await;
                break;
            }
            Ok(read) => {
                for chunk in buffer[..read].chunks(MAX_STREAM_FRAME_PAYLOAD) {
                    let (session_pending_bytes, stream_pending_bytes) =
                        enqueue_server_egress_data(stream_id, chunk.to_vec(), &egress).await;
                    if stream_pending_bytes > MAX_PENDING_EGRESS_BYTES_PER_STREAM {
                        wait_for_server_egress_stream_capacity(stream_id, &egress).await;
                    } else if session_pending_bytes > MAX_PENDING_EGRESS_BYTES {
                        wait_for_server_egress_capacity(&egress).await;
                    }
                    egress.notify.notify_one();
                }
            }
            Err(error) => {
                let _ = close_server_stream(
                    stream_id,
                    format!("upstream read failed: {error}"),
                    &egress,
                    &snapshot,
                    &streams,
                )
                .await;
                break;
            }
        }
    }
}

async fn run_upstream_writer(
    stream_id: u64,
    mut writer: OwnedWriteHalf,
    mut inbound_rx: mpsc::Receiver<Vec<u8>>,
    egress: ServerEgress,
    snapshot: Arc<RwLock<ServerSnapshot>>,
    streams: ServerStreamMap,
) {
    while let Some(data) = inbound_rx.recv().await {
        if let Err(error) = writer.write_all(&data).await {
            let _ = close_server_stream(
                stream_id,
                format!("upstream write failed: {error}"),
                &egress,
                &snapshot,
                &streams,
            )
            .await;
            return;
        }
    }
}

async fn close_server_stream(
    stream_id: u64,
    reason: String,
    egress: &ServerEgress,
    snapshot: &Arc<RwLock<ServerSnapshot>>,
    streams: &ServerStreamMap,
) -> Result<(), TransportError> {
    let removed = {
        let mut state = streams.lock().await;
        let removed = state.remove(&stream_id);
        snapshot.write().await.active_streams = u64::try_from(state.len()).unwrap_or(u64::MAX);
        removed
    };

    if let Some(removed) = removed {
        removed.reader_abort.abort();
        enqueue_server_egress_close(stream_id, reason, egress).await;
        egress.notify.notify_one();
    }

    Ok(())
}

async fn cleanup_streams(snapshot: &Arc<RwLock<ServerSnapshot>>, streams: &ServerStreamMap) {
    let removed = {
        let mut state = streams.lock().await;
        state.drain().map(|(_, stream)| stream).collect::<Vec<_>>()
    };
    for stream in removed {
        stream.reader_abort.abort();
        stream.writer_abort.abort();
    }
    snapshot.write().await.active_streams = 0;
}

async fn run_frame_writer<W>(
    mut writer: W,
    session_key: [u8; 32],
    mut control_frame_rx: mpsc::Receiver<ControlFrame>,
    mut data_frame_rx: mpsc::Receiver<ControlFrame>,
    snapshot: Arc<RwLock<ServerSnapshot>>,
) -> Result<(), TransportError>
where
    W: AsyncWrite + Unpin,
{
    let mut outgoing_seq = 0_u64;
    let mut control_closed = false;
    let mut data_closed = false;
    let mut consecutive_control_frames = 0_usize;

    loop {
        let prefer_data = !data_closed
            && !control_closed
            && consecutive_control_frames >= WRITER_CONTROL_BURST_LIMIT;
        let (frame, from_control) = if prefer_data {
            tokio::select! {
                biased;
                maybe_frame = data_frame_rx.recv(), if !data_closed => {
                    match maybe_frame {
                        Some(frame) => (frame, false),
                        None => {
                            data_closed = true;
                            if control_closed {
                                break;
                            }
                            continue;
                        }
                    }
                }
                maybe_frame = control_frame_rx.recv(), if !control_closed => {
                    match maybe_frame {
                        Some(frame) => (frame, true),
                        None => {
                            control_closed = true;
                            if data_closed {
                                break;
                            }
                            continue;
                        }
                    }
                }
                else => break,
            }
        } else {
            tokio::select! {
                biased;
                maybe_frame = control_frame_rx.recv(), if !control_closed => {
                    match maybe_frame {
                        Some(frame) => (frame, true),
                        None => {
                            control_closed = true;
                            if data_closed {
                                break;
                            }
                            continue;
                        }
                    }
                }
                maybe_frame = data_frame_rx.recv(), if !data_closed => {
                    match maybe_frame {
                        Some(frame) => (frame, false),
                        None => {
                            data_closed = true;
                            if control_closed {
                                break;
                            }
                            continue;
                        }
                    }
                }
                else => break,
            }
        };

        let data_len = match &frame {
            ControlFrame::StreamData { data, .. } => u64::try_from(data.len()).unwrap_or(u64::MAX),
            _ => 0,
        };

        if from_control {
            consecutive_control_frames = consecutive_control_frames.saturating_add(1);
        } else {
            consecutive_control_frames = 0;
        }

        write_encrypted_frame(
            &mut writer,
            &session_key,
            Direction::ServerToClient,
            &mut outgoing_seq,
            &frame,
        )
        .await?;

        let mut guard = snapshot.write().await;
        guard.frames_out = guard.frames_out.saturating_add(1);
        guard.bytes_out = guard.bytes_out.saturating_add(data_len);
    }

    Ok(())
}

async fn resolve_target_addr(
    host: &str,
    port: u16,
    allow_private_targets: bool,
) -> Result<SocketAddr, TransportError> {
    if host.trim().is_empty() || port == 0 {
        return Err(TransportError::Protocol(
            "stream target host/port must be valid".to_string(),
        ));
    }

    let mut resolved = lookup_host((host, port)).await?;
    let Some(addr) = resolved.find(|addr| allow_private_targets || is_allowed_egress_ip(addr.ip()))
    else {
        return Err(TransportError::Protocol(format!(
            "target {host}:{port} resolved only to disallowed addresses"
        )));
    };

    Ok(addr)
}

fn is_allowed_egress_ip(ip: IpAddr) -> bool {
    match ip {
        IpAddr::V4(ip) => {
            !(ip.is_private()
                || ip.is_loopback()
                || ip.is_link_local()
                || ip.is_broadcast()
                || ip.is_documentation()
                || ip.is_unspecified()
                || ip.is_multicast())
        }
        IpAddr::V6(ip) => {
            !(ip.is_loopback()
                || ip.is_unspecified()
                || ip.is_multicast()
                || ip.is_unique_local()
                || ip.is_unicast_link_local())
        }
    }
}

fn verify_hello(config: &ServerConfig, hello: &HandshakeHello) -> Result<(), TransportError> {
    if hello.magic != PROTOCOL_MAGIC {
        return Err(TransportError::Protocol(format!(
            "unexpected handshake magic: {}",
            hello.magic
        )));
    }
    if hello.protocol_version != PROTOCOL_VERSION {
        return Err(TransportError::Protocol(format!(
            "unsupported protocol version: {}",
            hello.protocol_version
        )));
    }
    if hello.transport_profile_id != config.transport_profile_id {
        return Err(TransportError::Protocol(format!(
            "unexpected transport profile: {}",
            hello.transport_profile_id
        )));
    }
    Ok(())
}

async fn write_json_frame<T: serde::Serialize, W: AsyncWrite + Unpin>(
    stream: &mut W,
    value: &T,
) -> Result<(), TransportError> {
    let payload = serde_json::to_vec(value)?;
    let len = u32::try_from(payload.len())
        .map_err(|_| TransportError::Protocol("json frame too large".to_string()))?;
    stream.write_u32(len).await?;
    stream.write_all(&payload).await?;
    Ok(())
}

async fn read_json_frame<T: serde::de::DeserializeOwned, R: AsyncRead + Unpin>(
    stream: &mut R,
) -> Result<T, TransportError> {
    let len = stream.read_u32().await?;
    let mut payload = vec![0_u8; usize::try_from(len).unwrap_or(0)];
    stream.read_exact(&mut payload).await?;
    serde_json::from_slice(&payload).map_err(TransportError::Json)
}

async fn write_encrypted_frame<W: AsyncWrite + Unpin>(
    stream: &mut W,
    session_key: &[u8; 32],
    direction: Direction,
    sequence: &mut u64,
    frame: &ControlFrame,
) -> Result<(), TransportError> {
    let ciphertext = encrypt_frame(session_key, direction, *sequence, frame)?;
    let len = u32::try_from(ciphertext.len())
        .map_err(|_| TransportError::Protocol("encrypted frame too large".to_string()))?;
    stream.write_u64(*sequence).await?;
    stream.write_u32(len).await?;
    stream.write_all(&ciphertext).await?;
    *sequence = sequence.saturating_add(1);
    Ok(())
}

async fn read_encrypted_frame<R: AsyncRead + Unpin>(
    stream: &mut R,
    session_key: &[u8; 32],
    direction: Direction,
    expected_sequence: &mut u64,
) -> Result<ControlFrame, TransportError> {
    let sequence = stream.read_u64().await?;
    if sequence != *expected_sequence {
        return Err(TransportError::Protocol(format!(
            "unexpected frame sequence: expected {} got {}",
            *expected_sequence, sequence
        )));
    }

    let len = stream.read_u32().await?;
    let mut ciphertext = vec![0_u8; usize::try_from(len).unwrap_or(0)];
    stream.read_exact(&mut ciphertext).await?;
    let frame = decrypt_frame(session_key, direction, sequence, &ciphertext)?;
    *expected_sequence = expected_sequence.saturating_add(1);
    Ok(frame)
}
