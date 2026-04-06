use std::{
    collections::{HashMap, HashSet, VecDeque},
    sync::Arc,
};

use tokio::{
    io::{AsyncRead, AsyncReadExt, AsyncWrite, AsyncWriteExt},
    net::TcpStream,
    sync::{mpsc, oneshot, watch, Mutex, Notify, RwLock},
    time::{interval, sleep, timeout, MissedTickBehavior},
};

use crate::{
    crypto::{
        client_proof, decrypt_frame, derive_session_key, encrypt_frame, random_nonce, server_proof,
        unix_timestamp_ms, Direction,
    },
    error::TransportError,
    model::{
        ClientConfig, ControlFrame, HandshakeHello, HandshakeWelcome, SessionSnapshot,
        StreamTarget, PROTOCOL_MAGIC, PROTOCOL_VERSION,
    },
};

const CONTROL_FRAME_CHANNEL_CAPACITY: usize = 256;
const DATA_FRAME_CHANNEL_CAPACITY: usize = 8;
const CONTROL_COMMAND_CHANNEL_CAPACITY: usize = 256;
const DATA_COMMAND_CHANNEL_CAPACITY: usize = 4;
const STREAM_CHANNEL_CAPACITY: usize = 96;
const MAX_STREAM_FRAME_PAYLOAD: usize = 8 * 1024;
const CONTENDED_STREAM_FRAME_PAYLOAD: usize = 4 * 1024;
const HEAVILY_CONTENDED_STREAM_FRAME_PAYLOAD: usize = 1024;
const MAX_INBOUND_STREAM_FRAME_PAYLOAD: usize = 16 * 1024;
const CONTENDED_INBOUND_STREAM_FRAME_PAYLOAD: usize = 2 * 1024;
const HEAVILY_CONTENDED_INBOUND_STREAM_FRAME_PAYLOAD: usize = 1024;
const MAX_PENDING_INBOUND_BYTES: usize = 8 * 1024 * 1024;
const MAX_PENDING_INBOUND_BYTES_PER_STREAM: usize = 512 * 1024;
const MAX_PENDING_INBOUND_BYTES_PER_STREAM_WITH_SIBLINGS: usize = 16 * 1024;
const WRITER_CONTROL_BURST_LIMIT: usize = 2;

#[derive(Debug, Clone)]
struct ClientSessionCommandBus {
    control_tx: mpsc::Sender<ClientSessionCommand>,
    data_tx: mpsc::Sender<ClientSessionCommand>,
}

#[derive(Debug, Clone)]
pub struct ClientHandle {
    snapshot: Arc<RwLock<SessionSnapshot>>,
    shutdown_tx: watch::Sender<bool>,
    session_commands: Arc<RwLock<Option<ClientSessionCommandBus>>>,
}

impl ClientHandle {
    pub fn snapshot_handle(&self) -> Arc<RwLock<SessionSnapshot>> {
        self.snapshot.clone()
    }

    pub async fn snapshot(&self) -> SessionSnapshot {
        self.snapshot.read().await.clone()
    }

    pub async fn open_stream(&self, target: StreamTarget) -> Result<ClientStream, TransportError> {
        let command_bus = self.session_commands.read().await.clone().ok_or_else(|| {
            TransportError::Protocol("Helix session is not ready for opening streams".to_string())
        })?;

        let (respond_to, response_rx) = oneshot::channel();
        command_bus
            .control_tx
            .send(ClientSessionCommand::OpenStream { target, respond_to })
            .await
            .map_err(|_| TransportError::ChannelClosed("client session open stream"))?;

        match response_rx.await {
            Ok(Ok(stream)) => Ok(stream),
            Ok(Err(error)) => Err(TransportError::Protocol(error)),
            Err(_) => Err(TransportError::ChannelClosed("client stream response")),
        }
    }

    pub async fn shutdown(&self) {
        let _ = self.shutdown_tx.send(true);
    }
}

#[derive(Debug)]
pub struct ClientStream {
    stream_id: u64,
    target: StreamTarget,
    inbound_rx: mpsc::Receiver<Vec<u8>>,
    writer: ClientStreamWriter,
}

impl ClientStream {
    pub fn stream_id(&self) -> u64 {
        self.stream_id
    }

    pub fn target(&self) -> &StreamTarget {
        &self.target
    }

    pub fn writer(&self) -> ClientStreamWriter {
        self.writer.clone()
    }

    pub async fn recv(&mut self) -> Option<Vec<u8>> {
        self.inbound_rx.recv().await
    }

    pub async fn close(&self, reason: impl Into<String>) -> Result<(), TransportError> {
        self.writer.close(reason).await
    }

    pub async fn finish(&self) -> Result<(), TransportError> {
        self.writer.finish().await
    }
}

#[derive(Debug, Clone)]
pub struct ClientStreamWriter {
    stream_id: u64,
    session_commands: Arc<RwLock<Option<ClientSessionCommandBus>>>,
}

impl ClientStreamWriter {
    pub async fn send(&self, data: Vec<u8>) -> Result<(), TransportError> {
        let command_bus = self.session_commands.read().await.clone().ok_or_else(|| {
            TransportError::Protocol(
                "Helix session is reconnecting and is not ready for writes".to_string(),
            )
        })?;

        command_bus
            .data_tx
            .send(ClientSessionCommand::SendStreamData {
                stream_id: self.stream_id,
                data,
            })
            .await
            .map_err(|_| TransportError::ChannelClosed("client stream send"))
    }

    pub async fn close(&self, reason: impl Into<String>) -> Result<(), TransportError> {
        let command_bus = self.session_commands.read().await.clone().ok_or_else(|| {
            TransportError::Protocol(
                "Helix session is reconnecting and is not ready for close".to_string(),
            )
        })?;

        command_bus
            .data_tx
            .send(ClientSessionCommand::CloseStream {
                stream_id: self.stream_id,
                reason: reason.into(),
            })
            .await
            .map_err(|_| TransportError::ChannelClosed("client stream close"))
    }

    pub async fn finish(&self) -> Result<(), TransportError> {
        let command_bus = self.session_commands.read().await.clone().ok_or_else(|| {
            TransportError::Protocol(
                "Helix session is reconnecting and is not ready for finish".to_string(),
            )
        })?;

        command_bus
            .data_tx
            .send(ClientSessionCommand::FinishStream {
                stream_id: self.stream_id,
            })
            .await
            .map_err(|_| TransportError::ChannelClosed("client stream finish"))
    }
}

#[derive(Debug)]
enum ClientSessionCommand {
    OpenStream {
        target: StreamTarget,
        respond_to: oneshot::Sender<Result<ClientStream, String>>,
    },
    SendStreamData {
        stream_id: u64,
        data: Vec<u8>,
    },
    FinishStream {
        stream_id: u64,
    },
    CloseStream {
        stream_id: u64,
        reason: String,
    },
}

#[derive(Debug)]
struct PendingClientStream {
    target: StreamTarget,
    inbound_tx: mpsc::Sender<Vec<u8>>,
    inbound_rx: Option<mpsc::Receiver<Vec<u8>>>,
    respond_to: oneshot::Sender<Result<ClientStream, String>>,
}

#[derive(Debug, Default)]
struct ClientSessionState {
    next_stream_id: u64,
    opening: HashMap<u64, PendingClientStream>,
    active: HashMap<u64, mpsc::Sender<Vec<u8>>>,
    aborting_inbound: HashSet<u64>,
    locally_stalled: HashSet<u64>,
    pending_data: HashMap<u64, VecDeque<Vec<u8>>>,
    data_schedule: VecDeque<u64>,
    pending_finishes: HashSet<u64>,
    pending_closes: HashMap<u64, String>,
}

#[derive(Debug)]
enum ClientInboundAction {
    StreamData { stream_id: u64, data: Vec<u8> },
    StreamClose { stream_id: u64, reason: String },
}

#[derive(Debug, Default)]
struct ClientInboundState {
    pending_data: HashMap<u64, VecDeque<Vec<u8>>>,
    pending_bytes_by_stream: HashMap<u64, usize>,
    pending_closes: HashMap<u64, String>,
    schedule: VecDeque<u64>,
    pending_bytes: usize,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum ClientInboundEnqueueResult {
    Accepted { session_pending_bytes: usize },
    StreamQuotaExceeded,
    IgnoredClosing,
}

#[derive(Debug, Clone)]
struct ClientInbound {
    state: Arc<Mutex<ClientInboundState>>,
    notify: Arc<Notify>,
}

pub fn spawn_client(config: ClientConfig) -> ClientHandle {
    let snapshot = Arc::new(RwLock::new(SessionSnapshot {
        status: "starting".to_string(),
        active_route: Some(config.route.endpoint_ref.clone()),
        ..SessionSnapshot::default()
    }));
    let session_commands = Arc::new(RwLock::new(None));
    let session_state = Arc::new(Mutex::new(ClientSessionState::default()));
    let inbound = ClientInbound {
        state: Arc::new(Mutex::new(ClientInboundState::default())),
        notify: Arc::new(Notify::new()),
    };
    let (shutdown_tx, shutdown_rx) = watch::channel(false);

    tokio::spawn(run_client_loop(
        config,
        snapshot.clone(),
        shutdown_rx,
        session_commands.clone(),
        session_state,
        inbound,
    ));

    ClientHandle {
        snapshot,
        shutdown_tx,
        session_commands,
    }
}

fn enable_low_latency_mode(stream: &TcpStream) {
    let _ = stream.set_nodelay(true);
}

fn sender_queue_depth<T>(sender: &mpsc::Sender<T>) -> u32 {
    let used = sender.max_capacity().saturating_sub(sender.capacity());
    u32::try_from(used).unwrap_or(u32::MAX)
}

fn combined_sender_queue_depth<T>(primary: &mpsc::Sender<T>, secondary: &mpsc::Sender<T>) -> u32 {
    sender_queue_depth(primary).saturating_add(sender_queue_depth(secondary))
}

fn split_stream_payload(data: Vec<u8>) -> Vec<Vec<u8>> {
    data.chunks(MAX_STREAM_FRAME_PAYLOAD)
        .map(|chunk| chunk.to_vec())
        .collect()
}

fn outbound_stream_frame_payload(stream_count: usize) -> usize {
    if stream_count >= 6 {
        HEAVILY_CONTENDED_STREAM_FRAME_PAYLOAD
    } else if stream_count >= 3 {
        CONTENDED_STREAM_FRAME_PAYLOAD
    } else {
        MAX_STREAM_FRAME_PAYLOAD
    }
}

fn inbound_stream_frame_payload(stream_count: usize) -> usize {
    if stream_count >= 4 {
        HEAVILY_CONTENDED_INBOUND_STREAM_FRAME_PAYLOAD
    } else if stream_count >= 2 {
        CONTENDED_INBOUND_STREAM_FRAME_PAYLOAD
    } else {
        MAX_INBOUND_STREAM_FRAME_PAYLOAD
    }
}

fn schedule_client_stream(state: &mut ClientSessionState, stream_id: u64) {
    if !state
        .data_schedule
        .iter()
        .any(|scheduled| *scheduled == stream_id)
    {
        state.data_schedule.push_back(stream_id);
    }
}

fn schedule_client_stream_front(state: &mut ClientSessionState, stream_id: u64) {
    if !state
        .data_schedule
        .iter()
        .any(|scheduled| *scheduled == stream_id)
    {
        state.data_schedule.push_front(stream_id);
    }
}

fn schedule_client_inbound_stream(state: &mut ClientInboundState, stream_id: u64) {
    if !state
        .schedule
        .iter()
        .any(|scheduled| *scheduled == stream_id)
    {
        state.schedule.push_back(stream_id);
    }
}

fn schedule_client_inbound_stream_front(state: &mut ClientInboundState, stream_id: u64) {
    if !state
        .schedule
        .iter()
        .any(|scheduled| *scheduled == stream_id)
    {
        state.schedule.push_front(stream_id);
    }
}

async fn set_frame_queue_depth(snapshot: &Arc<RwLock<SessionSnapshot>>, depth: u32) {
    let mut guard = snapshot.write().await;
    guard.frame_queue_depth = depth;
    guard.frame_queue_peak = guard.frame_queue_peak.max(depth);
}

async fn enqueue_client_stream_data(
    stream_id: u64,
    data: Vec<u8>,
    session_state: &Arc<Mutex<ClientSessionState>>,
) {
    let chunks = split_stream_payload(data);
    if chunks.is_empty() {
        return;
    }

    let mut state = session_state.lock().await;
    let is_new_stream = !state.pending_data.contains_key(&stream_id);
    let queue = state.pending_data.entry(stream_id).or_default();
    queue.extend(chunks);
    if is_new_stream {
        schedule_client_stream_front(&mut state, stream_id);
    }
}

async fn enqueue_client_stream_close(
    stream_id: u64,
    reason: String,
    session_state: &Arc<Mutex<ClientSessionState>>,
) {
    let mut state = session_state.lock().await;
    state.pending_closes.insert(stream_id, reason);
    schedule_client_stream(&mut state, stream_id);
}

async fn enqueue_client_stream_finish(
    stream_id: u64,
    session_state: &Arc<Mutex<ClientSessionState>>,
) {
    let mut state = session_state.lock().await;
    state.pending_finishes.insert(stream_id);
    schedule_client_stream(&mut state, stream_id);
}

async fn send_client_priority_close(
    stream_id: u64,
    reason: String,
    session_commands: &Arc<RwLock<Option<ClientSessionCommandBus>>>,
    data_command_tx: &mpsc::Sender<ClientSessionCommand>,
) {
    let close_command = ClientSessionCommand::CloseStream { stream_id, reason };
    let control_command_tx = session_commands
        .read()
        .await
        .as_ref()
        .map(|command_bus| command_bus.control_tx.clone());

    match control_command_tx
        .as_ref()
        .unwrap_or(data_command_tx)
        .try_send(close_command)
    {
        Ok(()) => {}
        Err(mpsc::error::TrySendError::Full(command)) => {
            if let Some(control_command_tx) = control_command_tx {
                tokio::spawn(async move {
                    let _ = control_command_tx.send(command).await;
                });
            } else {
                let data_command_tx = data_command_tx.clone();
                tokio::spawn(async move {
                    let _ = data_command_tx.send(command).await;
                });
            }
        }
        Err(mpsc::error::TrySendError::Closed(_)) => {}
    }
}

async fn requeue_client_stream_frame(
    frame: ControlFrame,
    session_state: &Arc<Mutex<ClientSessionState>>,
) {
    let mut state = session_state.lock().await;
    match frame {
        ControlFrame::StreamData { stream_id, data } => {
            state
                .pending_data
                .entry(stream_id)
                .or_default()
                .push_front(data);
            schedule_client_stream(&mut state, stream_id);
        }
        ControlFrame::StreamFinish { stream_id } => {
            state.pending_finishes.insert(stream_id);
            schedule_client_stream(&mut state, stream_id);
        }
        ControlFrame::StreamClose { stream_id, reason } => {
            state.pending_closes.insert(stream_id, reason);
            schedule_client_stream(&mut state, stream_id);
        }
        _ => {}
    }
}

async fn enqueue_client_inbound_data(
    stream_id: u64,
    data: Vec<u8>,
    inbound: &ClientInbound,
    session_state: &Arc<Mutex<ClientSessionState>>,
) -> ClientInboundEnqueueResult {
    let active_stream_count = {
        let state = session_state.lock().await;
        state.active.len()
    };
    let mut state = inbound.state.lock().await;
    if state.pending_closes.contains_key(&stream_id) {
        return ClientInboundEnqueueResult::IgnoredClosing;
    }

    let is_new_stream = !state.pending_data.contains_key(&stream_id);

    let stream_pending_bytes = state
        .pending_bytes_by_stream
        .get(&stream_id)
        .copied()
        .unwrap_or(0);
    let inbound_stream_limit = if active_stream_count > 1 {
        MAX_PENDING_INBOUND_BYTES_PER_STREAM_WITH_SIBLINGS
    } else {
        MAX_PENDING_INBOUND_BYTES_PER_STREAM
    };
    if stream_pending_bytes.saturating_add(data.len()) > inbound_stream_limit {
        return ClientInboundEnqueueResult::StreamQuotaExceeded;
    }

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
        schedule_client_inbound_stream_front(&mut state, stream_id);
    } else {
        schedule_client_inbound_stream(&mut state, stream_id);
    }
    ClientInboundEnqueueResult::Accepted {
        session_pending_bytes: state.pending_bytes,
    }
}

async fn requeue_client_inbound_data(stream_id: u64, data: Vec<u8>, inbound: &ClientInbound) {
    let mut state = inbound.state.lock().await;
    state.pending_bytes = state.pending_bytes.saturating_add(data.len());
    let stream_pending_bytes = state
        .pending_bytes_by_stream
        .get(&stream_id)
        .copied()
        .unwrap_or(0);
    state
        .pending_bytes_by_stream
        .insert(stream_id, stream_pending_bytes.saturating_add(data.len()));
    state
        .pending_data
        .entry(stream_id)
        .or_default()
        .push_front(data);
    schedule_client_inbound_stream(&mut state, stream_id);
}

async fn enqueue_client_inbound_close(stream_id: u64, reason: String, inbound: &ClientInbound) {
    let mut state = inbound.state.lock().await;
    state.pending_closes.insert(stream_id, reason);
    schedule_client_inbound_stream(&mut state, stream_id);
}

async fn has_pending_client_inbound(inbound: &ClientInbound) -> bool {
    !inbound.state.lock().await.schedule.is_empty()
}

async fn dequeue_client_inbound_action(inbound: &ClientInbound) -> Option<ClientInboundAction> {
    let mut state = inbound.state.lock().await;

    while let Some(stream_id) = state.schedule.pop_front() {
        let stream_count = state.schedule.len().saturating_add(1);
        let mut drained_bytes = 0_usize;
        let mut should_remove = false;
        let data = if let Some(queue) = state.pending_data.get_mut(&stream_id) {
            let mut next = queue.pop_front();
            if let Some(chunk) = next.as_mut() {
                let limit = inbound_stream_frame_payload(stream_count);
                if chunk.len() > limit {
                    let remainder = chunk.split_off(limit);
                    queue.push_front(remainder);
                }
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

        if let Some(data) = data {
            if state.pending_data.contains_key(&stream_id)
                || state.pending_closes.contains_key(&stream_id)
            {
                schedule_client_inbound_stream(&mut state, stream_id);
            }
            return Some(ClientInboundAction::StreamData { stream_id, data });
        }

        if let Some(reason) = state.pending_closes.remove(&stream_id) {
            state.pending_bytes_by_stream.remove(&stream_id);
            return Some(ClientInboundAction::StreamClose { stream_id, reason });
        }
    }

    None
}

async fn wait_for_client_inbound_capacity(inbound: &ClientInbound) {
    loop {
        let notified = {
            let state = inbound.state.lock().await;
            if state.pending_bytes <= MAX_PENDING_INBOUND_BYTES {
                return;
            }
            inbound.notify.notified()
        };

        notified.await;
    }
}

async fn drop_client_inbound_stream(stream_id: u64, inbound: &ClientInbound) {
    let mut state = inbound.state.lock().await;
    if let Some(queue) = state.pending_data.remove(&stream_id) {
        let dropped_bytes = queue
            .iter()
            .map(Vec::len)
            .fold(0_usize, |acc, len| acc.saturating_add(len));
        state.pending_bytes = state.pending_bytes.saturating_sub(dropped_bytes);
    }
    state.pending_bytes_by_stream.remove(&stream_id);
    state.pending_closes.remove(&stream_id);
    state.schedule.retain(|scheduled| *scheduled != stream_id);
}

async fn has_pending_client_stream_frames(session_state: &Arc<Mutex<ClientSessionState>>) -> bool {
    !session_state.lock().await.data_schedule.is_empty()
}

async fn dequeue_client_stream_data_frame(
    session_state: &Arc<Mutex<ClientSessionState>>,
) -> Option<ControlFrame> {
    let mut state = session_state.lock().await;

    while let Some(stream_id) = state.data_schedule.pop_front() {
        let mut should_remove = false;
        let chunk = if let Some(queue) = state.pending_data.get_mut(&stream_id) {
            let next = queue.pop_front();
            if queue.is_empty() {
                should_remove = true;
            }
            next
        } else {
            None
        };

        if should_remove {
            state.pending_data.remove(&stream_id);
        }

        if let Some(mut data) = chunk {
            let limit = outbound_stream_frame_payload(state.data_schedule.len().saturating_add(1));
            if data.len() > limit {
                let remainder = data.split_off(limit);
                state
                    .pending_data
                    .entry(stream_id)
                    .or_default()
                    .push_front(remainder);
            }
            if state.pending_data.contains_key(&stream_id)
                || state.pending_finishes.contains(&stream_id)
                || state.pending_closes.contains_key(&stream_id)
            {
                schedule_client_stream(&mut state, stream_id);
            }
            return Some(ControlFrame::StreamData { stream_id, data });
        }

        if state.pending_finishes.remove(&stream_id) {
            if state.pending_closes.contains_key(&stream_id) {
                schedule_client_stream(&mut state, stream_id);
            }
            return Some(ControlFrame::StreamFinish { stream_id });
        }

        if let Some(reason) = state.pending_closes.remove(&stream_id) {
            return Some(ControlFrame::StreamClose { stream_id, reason });
        }
    }

    None
}

async fn run_client_loop(
    config: ClientConfig,
    snapshot: Arc<RwLock<SessionSnapshot>>,
    mut shutdown_rx: watch::Receiver<bool>,
    session_commands: Arc<RwLock<Option<ClientSessionCommandBus>>>,
    session_state: Arc<Mutex<ClientSessionState>>,
    inbound: ClientInbound,
) {
    loop {
        if *shutdown_rx.borrow() {
            break;
        }

        let (active_streams, pending_open_streams) = client_session_counts(&session_state).await;
        {
            let mut guard = snapshot.write().await;
            guard.status = "connecting".to_string();
            guard.ready = false;
            guard.connected = false;
            guard.resumed_last_session = false;
            guard.active_streams = active_streams;
            guard.pending_open_streams = pending_open_streams;
            guard.frame_queue_depth = 0;
            guard.last_error = None;
        }

        let dial_addr = config.route.dial_addr();
        let connect_result = timeout(config.connect_timeout, TcpStream::connect(&dial_addr)).await;

        match connect_result {
            Ok(Ok(stream)) => {
                enable_low_latency_mode(&stream);
                if let Err(error) = run_client_session(
                    &config,
                    stream,
                    snapshot.clone(),
                    &mut shutdown_rx,
                    session_commands.clone(),
                    session_state.clone(),
                    inbound.clone(),
                )
                .await
                {
                    let (active_streams, pending_open_streams) =
                        client_session_counts(&session_state).await;
                    let mut guard = snapshot.write().await;
                    guard.status = "degraded".to_string();
                    guard.ready = false;
                    guard.connected = false;
                    guard.resumed_last_session = false;
                    guard.active_streams = active_streams;
                    guard.pending_open_streams = pending_open_streams;
                    guard.frame_queue_depth = 0;
                    guard.reconnect_attempts += 1;
                    guard.last_error = Some(error.to_string());
                }
            }
            Ok(Err(error)) => {
                let (active_streams, pending_open_streams) =
                    client_session_counts(&session_state).await;
                let mut guard = snapshot.write().await;
                guard.status = "degraded".to_string();
                guard.ready = false;
                guard.connected = false;
                guard.resumed_last_session = false;
                guard.active_streams = active_streams;
                guard.pending_open_streams = pending_open_streams;
                guard.frame_queue_depth = 0;
                guard.reconnect_attempts += 1;
                guard.last_error = Some(error.to_string());
            }
            Err(_) => {
                let (active_streams, pending_open_streams) =
                    client_session_counts(&session_state).await;
                let mut guard = snapshot.write().await;
                guard.status = "degraded".to_string();
                guard.ready = false;
                guard.connected = false;
                guard.resumed_last_session = false;
                guard.active_streams = active_streams;
                guard.pending_open_streams = pending_open_streams;
                guard.frame_queue_depth = 0;
                guard.reconnect_attempts += 1;
                guard.last_error = Some(format!("connect timeout while dialing {dial_addr}"));
            }
        }

        if *shutdown_rx.borrow() {
            break;
        }

        if wait_for_shutdown_or_delay(&mut shutdown_rx, config.reconnect_delay).await {
            break;
        }
    }
}

async fn run_client_session(
    config: &ClientConfig,
    mut stream: TcpStream,
    snapshot: Arc<RwLock<SessionSnapshot>>,
    shutdown_rx: &mut watch::Receiver<bool>,
    session_commands: Arc<RwLock<Option<ClientSessionCommandBus>>>,
    session_state: Arc<Mutex<ClientSessionState>>,
    inbound: ClientInbound,
) -> Result<(), TransportError> {
    let client_nonce = random_nonce();
    let prior_session_id = snapshot.read().await.session_id.clone();
    let mut hello = HandshakeHello {
        magic: PROTOCOL_MAGIC.to_string(),
        protocol_version: PROTOCOL_VERSION,
        manifest_id: config.manifest_id.clone(),
        transport_profile_id: config.transport_profile_id.clone(),
        profile_family: config.profile_family.clone(),
        profile_version: config.profile_version,
        policy_version: config.policy_version,
        session_mode: config.session_mode.clone(),
        route_ref: config.route.endpoint_ref.clone(),
        resume_session_id: prior_session_id.clone(),
        client_nonce,
        timestamp_ms: unix_timestamp_ms(),
        proof: [0_u8; 32],
    };
    hello.proof = client_proof(&config.token, &hello)?;

    write_json_frame(&mut stream, &hello).await?;
    let welcome = timeout(
        config.connect_timeout,
        read_json_frame::<HandshakeWelcome, _>(&mut stream),
    )
    .await
    .map_err(|_| TransportError::Timeout("server handshake welcome timed out".to_string()))??;

    if !welcome.accepted {
        return Err(TransportError::Protocol(
            welcome
                .error
                .unwrap_or_else(|| "server rejected the session".to_string()),
        ));
    }

    if welcome.magic != PROTOCOL_MAGIC {
        return Err(TransportError::Protocol(format!(
            "unexpected handshake magic: {}",
            welcome.magic
        )));
    }

    if welcome.transport_profile_id != config.transport_profile_id {
        return Err(TransportError::Protocol(format!(
            "transport profile mismatch: expected {} got {}",
            config.transport_profile_id, welcome.transport_profile_id
        )));
    }

    let expected_server_proof = server_proof(&config.token, &welcome, &hello)?;
    if welcome.proof != expected_server_proof {
        return Err(TransportError::Protocol(
            "server proof validation failed".to_string(),
        ));
    }

    let session_key = derive_session_key(
        &config.token,
        &welcome.session_id,
        &config.transport_profile_id,
        &hello.client_nonce,
        &welcome.server_nonce,
    )?;

    let resumed_last_session = prior_session_id
        .as_ref()
        .map(|session_id| session_id == &welcome.session_id && welcome.resumed)
        .unwrap_or(false);

    if prior_session_id.is_some() && !resumed_last_session {
        reset_client_runtime_state(
            &snapshot,
            &session_state,
            &inbound,
            "client session replaced",
        )
        .await;
    }

    let (active_streams, pending_open_streams) = client_session_counts(&session_state).await;

    let remote_addr = stream
        .peer_addr()
        .map(|addr| addr.to_string())
        .unwrap_or_else(|_| config.route.dial_addr());
    let (reader, writer) = stream.into_split();
    let (control_frame_tx, control_frame_rx) = mpsc::channel(CONTROL_FRAME_CHANNEL_CAPACITY);
    let (data_frame_tx, data_frame_rx) = mpsc::channel(DATA_FRAME_CHANNEL_CAPACITY);
    let (control_command_tx, mut control_command_rx) =
        mpsc::channel(CONTROL_COMMAND_CHANNEL_CAPACITY);
    let (data_command_tx, data_command_rx) = mpsc::channel(DATA_COMMAND_CHANNEL_CAPACITY);
    *session_commands.write().await = Some(ClientSessionCommandBus {
        control_tx: control_command_tx.clone(),
        data_tx: data_command_tx.clone(),
    });
    let read_timeout = config
        .heartbeat_interval
        .checked_mul(3)
        .unwrap_or(config.heartbeat_interval);

    let mut writer_task = tokio::spawn(run_frame_writer(
        writer,
        session_key,
        control_frame_rx,
        data_frame_rx,
        snapshot.clone(),
    ));

    if resumed_last_session {
        resend_pending_client_opens(&session_state, &control_frame_tx, &data_frame_tx, &snapshot)
            .await?;
    }

    let mut data_scheduler_task = tokio::spawn(run_client_data_scheduler(
        data_command_rx,
        control_frame_tx.clone(),
        data_frame_tx.clone(),
        session_state.clone(),
        snapshot.clone(),
    ));
    let mut inbound_scheduler_task = tokio::spawn(run_client_inbound_scheduler(
        inbound.clone(),
        session_state.clone(),
        snapshot.clone(),
        session_commands.clone(),
        data_command_tx.clone(),
    ));

    {
        let mut guard = snapshot.write().await;
        guard.status = "warming".to_string();
        guard.ready = false;
        guard.connected = true;
        guard.session_id = Some(welcome.session_id.clone());
        guard.resumed_last_session = resumed_last_session;
        guard.remote_addr = Some(remote_addr);
        guard.active_streams = active_streams;
        guard.pending_open_streams = pending_open_streams;
        guard.frame_queue_depth = 0;
        guard.last_error = None;
    }

    control_frame_tx
        .send(ControlFrame::Ping {
            sent_at_ms: unix_timestamp_ms(),
        })
        .await
        .map_err(|_| TransportError::ChannelClosed("client warmup ping"))?;
    let mut reader_task = tokio::spawn(run_frame_reader(
        reader,
        session_key,
        read_timeout,
        snapshot.clone(),
        session_state.clone(),
        inbound.clone(),
        session_commands.clone(),
        data_command_tx.clone(),
    ));

    let mut heartbeat = interval(config.heartbeat_interval);
    heartbeat.set_missed_tick_behavior(MissedTickBehavior::Skip);

    let session_result: Result<(), TransportError> = loop {
        tokio::select! {
            biased;
            changed = shutdown_rx.changed() => {
                if changed.is_ok() && *shutdown_rx.borrow() {
                    let _ = control_frame_tx.send(ControlFrame::Close {
                        reason: "client-shutdown".to_string(),
                    }).await;
                    break Ok(());
                }
            }
            reader_result = &mut reader_task => {
                match reader_result {
                    Ok(result) => break result,
                    Err(error) => break Err(TransportError::Protocol(format!("client reader task failed: {error}"))),
                }
            }
            writer_result = &mut writer_task => {
                match writer_result {
                    Ok(result) => break result,
                    Err(error) => break Err(TransportError::Protocol(format!("client writer task failed: {error}"))),
                }
            }
            scheduler_result = &mut data_scheduler_task => {
                match scheduler_result {
                    Ok(result) => break result,
                    Err(error) => break Err(TransportError::Protocol(format!("client data scheduler task failed: {error}"))),
                }
            }
            inbound_result = &mut inbound_scheduler_task => {
                match inbound_result {
                    Ok(result) => break result,
                    Err(error) => break Err(TransportError::Protocol(format!("client inbound scheduler task failed: {error}"))),
                }
            }
            maybe_command = control_command_rx.recv() => {
                let Some(command) = maybe_command else {
                    break Err(TransportError::ChannelClosed("client control command receiver"));
                };

                handle_client_command(
                    command,
                    &control_frame_tx,
                    &data_frame_tx,
                    &session_state,
                    &snapshot,
                ).await?;
            }
            _ = heartbeat.tick() => {
                let sent_at_ms = unix_timestamp_ms();
                control_frame_tx
                    .send(ControlFrame::Ping { sent_at_ms })
                    .await
                    .map_err(|_| TransportError::ChannelClosed("client heartbeat send"))?;
                set_frame_queue_depth(
                    &snapshot,
                    combined_sender_queue_depth(&control_frame_tx, &data_frame_tx),
                ).await;
            }
        }
    };

    *session_commands.write().await = None;

    reader_task.abort();
    writer_task.abort();
    data_scheduler_task.abort();
    inbound_scheduler_task.abort();

    {
        let (active_streams, pending_open_streams) = client_session_counts(&session_state).await;
        let mut guard = snapshot.write().await;
        guard.ready = false;
        guard.connected = false;
        guard.resumed_last_session = false;
        guard.active_streams = active_streams;
        guard.pending_open_streams = pending_open_streams;
        guard.frame_queue_depth = 0;
        if guard.status != "degraded" {
            guard.status = "degraded".to_string();
        }
    }

    if session_result.is_ok() && *shutdown_rx.borrow() {
        reset_client_runtime_state(
            &snapshot,
            &session_state,
            &inbound,
            "client session shutdown",
        )
        .await;
    }

    session_result
}

async fn handle_client_command(
    command: ClientSessionCommand,
    control_frame_tx: &mpsc::Sender<ControlFrame>,
    data_frame_tx: &mpsc::Sender<ControlFrame>,
    session_state: &Arc<Mutex<ClientSessionState>>,
    snapshot: &Arc<RwLock<SessionSnapshot>>,
) -> Result<(), TransportError> {
    match command {
        ClientSessionCommand::OpenStream { target, respond_to } => {
            validate_stream_target(&target)?;

            let (inbound_tx, inbound_rx) = mpsc::channel(STREAM_CHANNEL_CAPACITY);
            let (stream_id, pending_open_streams) = {
                let mut state = session_state.lock().await;
                state.next_stream_id = state.next_stream_id.saturating_add(1);
                let stream_id = state.next_stream_id;
                state.opening.insert(
                    stream_id,
                    PendingClientStream {
                        target: target.clone(),
                        inbound_tx,
                        inbound_rx: Some(inbound_rx),
                        respond_to,
                    },
                );
                (
                    stream_id,
                    u64::try_from(state.opening.len()).unwrap_or(u64::MAX),
                )
            };

            control_frame_tx
                .send(ControlFrame::StreamOpen {
                    stream_id,
                    target_host: target.host,
                    target_port: target.port,
                })
                .await
                .map_err(|_| TransportError::ChannelClosed("client stream open frame"))?;

            let mut guard = snapshot.write().await;
            guard.pending_open_streams = pending_open_streams;
            let depth = combined_sender_queue_depth(control_frame_tx, data_frame_tx);
            guard.frame_queue_depth = depth;
            guard.frame_queue_peak = guard.frame_queue_peak.max(depth);
        }
        ClientSessionCommand::SendStreamData { .. } => {
            return Err(TransportError::Protocol(
                "client stream data must be routed through the scheduler".to_string(),
            ));
        }
        ClientSessionCommand::FinishStream { stream_id } => {
            let (pending_open_streams, active_streams) = {
                let state = session_state.lock().await;
                (
                    u64::try_from(state.opening.len()).unwrap_or(u64::MAX),
                    u64::try_from(state.active.len()).unwrap_or(u64::MAX),
                )
            };
            let mut guard = snapshot.write().await;
            guard.pending_open_streams = pending_open_streams;
            guard.active_streams = active_streams;
            let depth = combined_sender_queue_depth(control_frame_tx, data_frame_tx);
            guard.frame_queue_depth = depth;
            guard.frame_queue_peak = guard.frame_queue_peak.max(depth);
            drop(guard);
            enqueue_client_stream_finish(stream_id, session_state).await;
        }
        ClientSessionCommand::CloseStream { stream_id, reason } => {
            let (pending_open_streams, active_streams) = {
                let state = session_state.lock().await;
                (
                    u64::try_from(state.opening.len()).unwrap_or(u64::MAX),
                    u64::try_from(state.active.len()).unwrap_or(u64::MAX),
                )
            };
            let mut guard = snapshot.write().await;
            guard.pending_open_streams = pending_open_streams;
            guard.active_streams = active_streams;
            let depth = combined_sender_queue_depth(control_frame_tx, data_frame_tx);
            guard.frame_queue_depth = depth;
            guard.frame_queue_peak = guard.frame_queue_peak.max(depth);
            drop(guard);
            enqueue_client_stream_close(stream_id, reason, session_state).await;
        }
    }

    Ok(())
}

async fn resend_pending_client_opens(
    session_state: &Arc<Mutex<ClientSessionState>>,
    control_frame_tx: &mpsc::Sender<ControlFrame>,
    data_frame_tx: &mpsc::Sender<ControlFrame>,
    snapshot: &Arc<RwLock<SessionSnapshot>>,
) -> Result<(), TransportError> {
    let pending_opens = {
        let state = session_state.lock().await;
        state
            .opening
            .iter()
            .map(|(stream_id, pending)| (*stream_id, pending.target.clone()))
            .collect::<Vec<_>>()
    };

    for (stream_id, target) in pending_opens {
        control_frame_tx
            .send(ControlFrame::StreamOpen {
                stream_id,
                target_host: target.host,
                target_port: target.port,
            })
            .await
            .map_err(|_| TransportError::ChannelClosed("client stream reopen frame"))?;
    }

    let mut guard = snapshot.write().await;
    let depth = combined_sender_queue_depth(control_frame_tx, data_frame_tx);
    guard.frame_queue_depth = depth;
    guard.frame_queue_peak = guard.frame_queue_peak.max(depth);
    Ok(())
}

async fn run_frame_writer<W>(
    mut writer: W,
    session_key: [u8; 32],
    mut control_frame_rx: mpsc::Receiver<ControlFrame>,
    mut data_frame_rx: mpsc::Receiver<ControlFrame>,
    snapshot: Arc<RwLock<SessionSnapshot>>,
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
            Direction::ClientToServer,
            &mut outgoing_seq,
            &frame,
        )
        .await?;

        let mut guard = snapshot.write().await;
        guard.sent_frames = guard.sent_frames.saturating_add(1);
        guard.bytes_sent = guard.bytes_sent.saturating_add(data_len);
    }

    Ok(())
}

async fn run_client_data_scheduler(
    mut data_command_rx: mpsc::Receiver<ClientSessionCommand>,
    control_frame_tx: mpsc::Sender<ControlFrame>,
    data_frame_tx: mpsc::Sender<ControlFrame>,
    session_state: Arc<Mutex<ClientSessionState>>,
    snapshot: Arc<RwLock<SessionSnapshot>>,
) -> Result<(), TransportError> {
    let mut data_channel_closed = false;
    let mut has_pending_frames = has_pending_client_stream_frames(&session_state).await;

    loop {
        let mut progressed = false;
        tokio::select! {
            next_frame = dequeue_client_stream_data_frame(&session_state), if has_pending_frames => {
                match next_frame {
                    Some(frame) => {
                        match data_frame_tx.try_send(frame) {
                            Ok(()) => {
                                set_frame_queue_depth(
                                    &snapshot,
                                    combined_sender_queue_depth(&control_frame_tx, &data_frame_tx),
                                ).await;
                                has_pending_frames = has_pending_client_stream_frames(&session_state).await;
                                progressed = true;
                            }
                            Err(mpsc::error::TrySendError::Full(frame)) => {
                                requeue_client_stream_frame(frame, &session_state).await;
                                has_pending_frames = true;
                            }
                            Err(mpsc::error::TrySendError::Closed(_)) => {
                                return Err(TransportError::ChannelClosed("client stream data frame"));
                            }
                        }
                    }
                    None => {
                        has_pending_frames = false;
                        if data_channel_closed {
                            break;
                        }
                    }
                }
            }
            maybe_command = data_command_rx.recv(), if !data_channel_closed => {
                match maybe_command {
                    Some(ClientSessionCommand::SendStreamData { stream_id, data }) => {
                        enqueue_client_stream_data(stream_id, data, &session_state).await;
                        has_pending_frames = true;
                        progressed = true;
                    }
                    Some(ClientSessionCommand::FinishStream { stream_id }) => {
                        enqueue_client_stream_finish(stream_id, &session_state).await;
                        has_pending_frames = true;
                        progressed = true;
                    }
                    Some(ClientSessionCommand::CloseStream { stream_id, reason }) => {
                        enqueue_client_stream_close(stream_id, reason, &session_state).await;
                        has_pending_frames = true;
                        progressed = true;
                    }
                    Some(other) => {
                        return Err(TransportError::Protocol(format!(
                            "unexpected client data scheduler command: {other:?}"
                        )));
                    }
                    None => {
                        data_channel_closed = true;
                        if !has_pending_frames {
                            break;
                        }
                    }
                }
            }
        }

        if !progressed && has_pending_frames {
            tokio::task::yield_now().await;
        }

        if data_channel_closed && !has_pending_frames {
            break;
        }
    }

    Ok(())
}

#[allow(clippy::too_many_arguments)]
async fn run_frame_reader<R>(
    mut reader: R,
    session_key: [u8; 32],
    read_timeout: std::time::Duration,
    snapshot: Arc<RwLock<SessionSnapshot>>,
    session_state: Arc<Mutex<ClientSessionState>>,
    inbound: ClientInbound,
    session_commands: Arc<RwLock<Option<ClientSessionCommandBus>>>,
    data_command_tx: mpsc::Sender<ClientSessionCommand>,
) -> Result<(), TransportError>
where
    R: AsyncRead + Unpin,
{
    let mut incoming_seq = 0_u64;

    loop {
        let frame = timeout(
            read_timeout,
            read_encrypted_frame(
                &mut reader,
                &session_key,
                Direction::ServerToClient,
                &mut incoming_seq,
            ),
        )
        .await
        .map_err(|_| TransportError::Timeout("client frame read timed out".to_string()))??;

        let data_len = match &frame {
            ControlFrame::StreamData { data, .. } => u64::try_from(data.len()).unwrap_or(u64::MAX),
            _ => 0,
        };

        {
            let mut guard = snapshot.write().await;
            guard.received_frames = guard.received_frames.saturating_add(1);
            guard.bytes_received = guard.bytes_received.saturating_add(data_len);
        }

        match frame {
            ControlFrame::Pong {
                sent_at_ms: echoed_sent_at_ms,
                ..
            } => {
                let now_ms = unix_timestamp_ms();
                let rtt_ms = now_ms.saturating_sub(echoed_sent_at_ms);
                let mut guard = snapshot.write().await;
                guard.status = "ready".to_string();
                guard.ready = true;
                guard.connected = true;
                guard.last_ping_rtt_ms = Some(u32::try_from(rtt_ms).unwrap_or(u32::MAX));
                guard.last_error = None;
            }
            ControlFrame::StreamOpened {
                stream_id,
                bind_target: _,
            } => {
                let (respond_to, pending_count, active_count, stream, forced_stalled_streams) = {
                    let mut state = session_state.lock().await;
                    let Some(mut pending) = state.opening.remove(&stream_id) else {
                        return Err(TransportError::Protocol(format!(
                            "server opened unknown client stream id {stream_id}"
                        )));
                    };
                    let inbound_rx = pending.inbound_rx.take().ok_or_else(|| {
                        TransportError::Protocol(format!(
                            "client stream receiver missing for stream {stream_id}"
                        ))
                    })?;
                    state.active.insert(stream_id, pending.inbound_tx);
                    let stream = ClientStream {
                        stream_id,
                        target: pending.target,
                        inbound_rx,
                        writer: ClientStreamWriter {
                            stream_id,
                            session_commands: session_commands.clone(),
                        },
                    };
                    let forced_stalled_streams = if state.active.len() > 1 {
                        let low_capacity_threshold = (STREAM_CHANNEL_CAPACITY * 2) / 3;
                        let stalled = state
                            .active
                            .iter()
                            .filter_map(|(active_stream_id, sender)| {
                                let is_current_stream = *active_stream_id == stream_id;
                                let is_locally_stalled =
                                    state.locally_stalled.contains(active_stream_id);
                                let receiver_is_saturated =
                                    sender.capacity() <= low_capacity_threshold;
                                if !is_current_stream
                                    && (is_locally_stalled || receiver_is_saturated)
                                {
                                    Some(*active_stream_id)
                                } else {
                                    None
                                }
                            })
                            .collect::<Vec<_>>();
                        for stalled_stream_id in &stalled {
                            state.aborting_inbound.insert(*stalled_stream_id);
                            state.active.remove(stalled_stream_id);
                            state.locally_stalled.remove(stalled_stream_id);
                        }
                        stalled
                    } else {
                        Vec::new()
                    };
                    (
                        pending.respond_to,
                        u64::try_from(state.opening.len()).unwrap_or(u64::MAX),
                        u64::try_from(state.active.len()).unwrap_or(u64::MAX),
                        stream,
                        forced_stalled_streams,
                    )
                };

                let _ = respond_to.send(Ok(stream));
                for stalled_stream_id in forced_stalled_streams {
                    drop_client_inbound_stream(stalled_stream_id, &inbound).await;
                    send_client_priority_close(
                        stalled_stream_id,
                        "client inbound receiver stalled under sibling load".to_string(),
                        &session_commands,
                        &data_command_tx,
                    )
                    .await;
                }
                let mut guard = snapshot.write().await;
                guard.pending_open_streams = pending_count;
                guard.active_streams = active_count;
                guard.max_concurrent_streams = guard.max_concurrent_streams.max(active_count);
            }
            ControlFrame::StreamData { stream_id, data } => {
                let (stream_known, stream_aborting) = {
                    let state = session_state.lock().await;
                    (
                        state.active.contains_key(&stream_id),
                        state.aborting_inbound.contains(&stream_id),
                    )
                };

                if stream_aborting {
                    continue;
                }

                if !stream_known {
                    return Err(TransportError::Protocol(format!(
                        "server delivered data for unknown client stream id {stream_id}"
                    )));
                }

                match enqueue_client_inbound_data(stream_id, data, &inbound, &session_state).await {
                    ClientInboundEnqueueResult::Accepted {
                        session_pending_bytes,
                    } => {
                        if session_pending_bytes > MAX_PENDING_INBOUND_BYTES {
                            wait_for_client_inbound_capacity(&inbound).await;
                        }
                    }
                    ClientInboundEnqueueResult::StreamQuotaExceeded => {
                        let close_reason = "client inbound backpressure limit exceeded".to_string();
                        let active_streams = {
                            let mut state = session_state.lock().await;
                            state.aborting_inbound.insert(stream_id);
                            state.active.remove(&stream_id);
                            state.locally_stalled.remove(&stream_id);
                            u64::try_from(state.active.len()).unwrap_or(u64::MAX)
                        };
                        drop_client_inbound_stream(stream_id, &inbound).await;
                        send_client_priority_close(
                            stream_id,
                            close_reason.clone(),
                            &session_commands,
                            &data_command_tx,
                        )
                        .await;
                        let mut guard = snapshot.write().await;
                        guard.active_streams = active_streams;
                        guard.last_error = Some(close_reason);
                    }
                    ClientInboundEnqueueResult::IgnoredClosing => {}
                }
                inbound.notify.notify_one();
            }
            ControlFrame::StreamFinish { .. } => {
                return Err(TransportError::Protocol(
                    "unexpected stream_finish received by client".to_string(),
                ));
            }
            ControlFrame::StreamClose { stream_id, reason } => {
                let (pending_response, pending_count, active_count) = {
                    let mut state = session_state.lock().await;
                    let pending = state
                        .opening
                        .remove(&stream_id)
                        .map(|pending| pending.respond_to);
                    state.aborting_inbound.remove(&stream_id);
                    (
                        pending,
                        u64::try_from(state.opening.len()).unwrap_or(u64::MAX),
                        u64::try_from(state.active.len()).unwrap_or(u64::MAX),
                    )
                };

                let had_pending_response = pending_response.is_some();

                if let Some(respond_to) = pending_response {
                    let _ = respond_to.send(Err(reason.clone()));
                }

                if !had_pending_response {
                    enqueue_client_inbound_close(stream_id, reason.clone(), &inbound).await;
                    inbound.notify.notify_one();
                }

                let mut guard = snapshot.write().await;
                guard.pending_open_streams = pending_count;
                guard.active_streams = active_count;
                guard.last_error = Some(reason);
            }
            ControlFrame::Close { reason } => {
                return Err(TransportError::Protocol(format!(
                    "server closed session: {reason}"
                )));
            }
            ControlFrame::Ping { .. } => {
                return Err(TransportError::Protocol(
                    "unexpected ping received by client".to_string(),
                ));
            }
            ControlFrame::StreamOpen { .. } => {
                return Err(TransportError::Protocol(
                    "unexpected server stream control frame shape".to_string(),
                ));
            }
        }
    }
}

async fn run_client_inbound_scheduler(
    inbound: ClientInbound,
    session_state: Arc<Mutex<ClientSessionState>>,
    snapshot: Arc<RwLock<SessionSnapshot>>,
    session_commands: Arc<RwLock<Option<ClientSessionCommandBus>>>,
    data_command_tx: mpsc::Sender<ClientSessionCommand>,
) -> Result<(), TransportError> {
    let mut has_pending_inbound = has_pending_client_inbound(&inbound).await;

    loop {
        if !has_pending_inbound {
            inbound.notify.notified().await;
            has_pending_inbound = has_pending_client_inbound(&inbound).await;
            continue;
        }

        let Some(action) = dequeue_client_inbound_action(&inbound).await else {
            has_pending_inbound = false;
            continue;
        };

        let progressed = match action {
            ClientInboundAction::StreamData { stream_id, data } => {
                let outbound = {
                    let state = session_state.lock().await;
                    state.active.get(&stream_id).cloned()
                };

                if let Some(outbound) = outbound {
                    match outbound.try_send(data) {
                        Ok(()) => {
                            inbound.notify.notify_waiters();
                            true
                        }
                        Err(mpsc::error::TrySendError::Full(data)) => {
                            let (has_siblings, active_streams) = {
                                let mut state = session_state.lock().await;
                                let has_siblings = state.active.len() > 1;
                                let active_streams = if has_siblings {
                                    state.aborting_inbound.insert(stream_id);
                                    state.active.remove(&stream_id);
                                    state.locally_stalled.remove(&stream_id);
                                    u64::try_from(state.active.len()).unwrap_or(u64::MAX)
                                } else {
                                    state.locally_stalled.insert(stream_id);
                                    u64::try_from(state.active.len()).unwrap_or(u64::MAX)
                                };
                                (has_siblings, active_streams)
                            };

                            if has_siblings {
                                drop(data);
                                drop_client_inbound_stream(stream_id, &inbound).await;
                                let close_reason =
                                    "client inbound receiver stalled under sibling load"
                                        .to_string();
                                send_client_priority_close(
                                    stream_id,
                                    close_reason.clone(),
                                    &session_commands,
                                    &data_command_tx,
                                )
                                .await;
                                let mut guard = snapshot.write().await;
                                guard.active_streams = active_streams;
                                guard.last_error = Some(close_reason);
                                inbound.notify.notify_waiters();
                                true
                            } else {
                                requeue_client_inbound_data(stream_id, data, &inbound).await;
                                false
                            }
                        }
                        Err(mpsc::error::TrySendError::Closed(_)) => {
                            let active_streams = {
                                let mut state = session_state.lock().await;
                                state.active.remove(&stream_id);
                                u64::try_from(state.active.len()).unwrap_or(u64::MAX)
                            };
                            snapshot.write().await.active_streams = active_streams;
                            inbound.notify.notify_waiters();
                            true
                        }
                    }
                } else {
                    inbound.notify.notify_waiters();
                    true
                }
            }
            ClientInboundAction::StreamClose { stream_id, reason } => {
                let active_streams = {
                    let mut state = session_state.lock().await;
                    state.active.remove(&stream_id);
                    u64::try_from(state.active.len()).unwrap_or(u64::MAX)
                };
                drop_client_inbound_stream(stream_id, &inbound).await;
                let mut guard = snapshot.write().await;
                guard.active_streams = active_streams;
                guard.last_error = Some(reason);
                inbound.notify.notify_waiters();
                true
            }
        };

        has_pending_inbound = has_pending_client_inbound(&inbound).await;
        if !progressed && has_pending_inbound {
            tokio::task::yield_now().await;
        }
    }
}

async fn client_session_counts(session_state: &Arc<Mutex<ClientSessionState>>) -> (u64, u64) {
    let state = session_state.lock().await;
    (
        u64::try_from(state.active.len()).unwrap_or(u64::MAX),
        u64::try_from(state.opening.len()).unwrap_or(u64::MAX),
    )
}

async fn cleanup_pending_open_streams(
    snapshot: &Arc<RwLock<SessionSnapshot>>,
    session_state: &Arc<Mutex<ClientSessionState>>,
    reason: &str,
) {
    let mut state = session_state.lock().await;
    for (_, pending) in state.opening.drain() {
        let _ = pending.respond_to.send(Err(reason.to_string()));
    }
    let active_streams = u64::try_from(state.active.len()).unwrap_or(u64::MAX);
    let pending_open_streams = u64::try_from(state.opening.len()).unwrap_or(u64::MAX);
    drop(state);

    let mut guard = snapshot.write().await;
    guard.active_streams = active_streams;
    guard.pending_open_streams = pending_open_streams;
    guard.frame_queue_depth = 0;
}

async fn reset_client_runtime_state(
    snapshot: &Arc<RwLock<SessionSnapshot>>,
    session_state: &Arc<Mutex<ClientSessionState>>,
    inbound: &ClientInbound,
    reason: &str,
) {
    cleanup_pending_open_streams(snapshot, session_state, reason).await;

    let mut state = session_state.lock().await;
    state.active.clear();
    state.aborting_inbound.clear();
    state.locally_stalled.clear();
    state.pending_data.clear();
    state.data_schedule.clear();
    state.pending_finishes.clear();
    state.pending_closes.clear();
    drop(state);

    {
        let mut state = inbound.state.lock().await;
        state.pending_data.clear();
        state.pending_bytes_by_stream.clear();
        state.pending_closes.clear();
        state.schedule.clear();
        state.pending_bytes = 0;
    }

    let mut guard = snapshot.write().await;
    guard.session_id = None;
    guard.resumed_last_session = false;
    guard.active_streams = 0;
    guard.pending_open_streams = 0;
    guard.frame_queue_depth = 0;
}

fn validate_stream_target(target: &StreamTarget) -> Result<(), TransportError> {
    if target.host.trim().is_empty() {
        return Err(TransportError::Protocol(
            "stream target host must not be empty".to_string(),
        ));
    }
    if target.port == 0 {
        return Err(TransportError::Protocol(
            "stream target port must not be zero".to_string(),
        ));
    }
    Ok(())
}

async fn wait_for_shutdown_or_delay(
    shutdown_rx: &mut watch::Receiver<bool>,
    delay: std::time::Duration,
) -> bool {
    if *shutdown_rx.borrow() {
        return true;
    }

    tokio::select! {
        changed = shutdown_rx.changed() => {
            changed.is_ok() && *shutdown_rx.borrow()
        }
        _ = sleep(delay) => false,
    }
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
    let mut payload = Vec::with_capacity(12 + ciphertext.len());
    payload.extend_from_slice(&sequence.to_be_bytes());
    payload.extend_from_slice(&len.to_be_bytes());
    payload.extend_from_slice(&ciphertext);
    stream.write_all(&payload).await?;
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
