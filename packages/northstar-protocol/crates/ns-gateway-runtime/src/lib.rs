#![forbid(unsafe_code)]

use ns_auth::{RequestedAccess, SessionTokenVerifier, VerifiedSessionToken};
use ns_core::{Capability, DatagramMode, ProtocolErrorCode, SessionId, SessionLimits, SessionMode};
use ns_observability::record_gateway_relay_guard;
use ns_session::{GatewayAdmissionContext, SessionController};
use ns_wire::{ClientHello, ServerHello};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use std::time::{Duration as StdDuration, Instant};
use thiserror::Error;
use tokio::sync::{OwnedSemaphorePermit, Semaphore};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GatewayAdmissionOutcome {
    pub token: VerifiedSessionToken,
    pub controller: SessionController,
    pub response: ServerHello,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct GatewayPreAuthBudgets {
    pub max_pending_hellos: usize,
    pub max_control_body_bytes: usize,
    pub handshake_deadline_ms: u64,
}

impl Default for GatewayPreAuthBudgets {
    fn default() -> Self {
        Self {
            max_pending_hellos: 256,
            max_control_body_bytes: 16 * 1024,
            handshake_deadline_ms: 1_000,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct GatewayRelayBudgets {
    pub max_active_relays: usize,
    pub max_relay_prebuffer_bytes: usize,
    pub relay_idle_timeout_ms: u64,
}

impl Default for GatewayRelayBudgets {
    fn default() -> Self {
        Self {
            max_active_relays: 256,
            max_relay_prebuffer_bytes: 64 * 1024,
            relay_idle_timeout_ms: 30_000,
        }
    }
}

impl GatewayRelayBudgets {
    fn validate(&self) -> Result<(), GatewayRuntimeError> {
        if self.max_active_relays == 0 {
            return Err(GatewayRuntimeError::InvalidBudget("max_active_relays"));
        }
        if self.max_relay_prebuffer_bytes == 0 {
            return Err(GatewayRuntimeError::InvalidBudget(
                "max_relay_prebuffer_bytes",
            ));
        }
        if self.relay_idle_timeout_ms == 0 {
            return Err(GatewayRuntimeError::InvalidBudget("relay_idle_timeout_ms"));
        }
        Ok(())
    }

    pub fn relay_idle_timeout(&self) -> StdDuration {
        StdDuration::from_millis(self.relay_idle_timeout_ms)
    }
}

impl GatewayPreAuthBudgets {
    fn validate(&self) -> Result<(), GatewayRuntimeError> {
        if self.max_pending_hellos == 0 {
            return Err(GatewayRuntimeError::InvalidBudget("max_pending_hellos"));
        }
        if self.max_control_body_bytes == 0 {
            return Err(GatewayRuntimeError::InvalidBudget("max_control_body_bytes"));
        }
        if self.handshake_deadline_ms == 0 {
            return Err(GatewayRuntimeError::InvalidBudget("handshake_deadline_ms"));
        }
        Ok(())
    }

    fn handshake_deadline(&self) -> StdDuration {
        StdDuration::from_millis(self.handshake_deadline_ms)
    }
}

#[derive(Clone, Debug)]
pub struct GatewayPreAuthGate {
    budgets: GatewayPreAuthBudgets,
    pending_hellos: Arc<Semaphore>,
}

impl GatewayPreAuthGate {
    pub fn new(budgets: GatewayPreAuthBudgets) -> Result<Self, GatewayRuntimeError> {
        budgets.validate()?;
        Ok(Self {
            pending_hellos: Arc::new(Semaphore::new(budgets.max_pending_hellos)),
            budgets,
        })
    }

    pub fn budgets(&self) -> &GatewayPreAuthBudgets {
        &self.budgets
    }

    pub fn try_begin_hello(&self) -> Result<PendingHelloPermit, GatewayRuntimeError> {
        let permit = self
            .pending_hellos
            .clone()
            .try_acquire_owned()
            .map_err(|_| GatewayRuntimeError::PreAuthOverloaded {
                max_pending_hellos: self.budgets.max_pending_hellos,
            })?;
        Ok(PendingHelloPermit {
            budgets: self.budgets.clone(),
            permit,
            started_at: Instant::now(),
        })
    }
}

#[derive(Debug)]
pub struct PendingHelloPermit {
    budgets: GatewayPreAuthBudgets,
    permit: OwnedSemaphorePermit,
    started_at: Instant,
}

impl PendingHelloPermit {
    pub fn enforce_control_body_size(
        &self,
        actual_bytes: usize,
    ) -> Result<(), GatewayRuntimeError> {
        if actual_bytes > self.budgets.max_control_body_bytes {
            return Err(GatewayRuntimeError::ControlBodyTooLarge {
                max_control_body_bytes: self.budgets.max_control_body_bytes,
                actual_bytes,
            });
        }
        Ok(())
    }

    pub fn enforce_handshake_deadline(&self) -> Result<(), GatewayRuntimeError> {
        let elapsed = self.started_at.elapsed();
        if elapsed > self.budgets.handshake_deadline() {
            return Err(GatewayRuntimeError::HandshakeDeadlineExceeded {
                handshake_deadline_ms: self.budgets.handshake_deadline_ms,
                elapsed_ms: elapsed.as_millis(),
            });
        }
        Ok(())
    }

    pub fn elapsed(&self) -> StdDuration {
        self.started_at.elapsed()
    }

    pub fn budgets(&self) -> &GatewayPreAuthBudgets {
        &self.budgets
    }

    pub fn pending_permit(&self) -> &OwnedSemaphorePermit {
        &self.permit
    }
}

#[derive(Clone, Debug)]
pub struct GatewayRelayGate {
    budgets: GatewayRelayBudgets,
    active_relays: Arc<Semaphore>,
}

impl GatewayRelayGate {
    pub fn new(budgets: GatewayRelayBudgets) -> Result<Self, GatewayRuntimeError> {
        budgets.validate()?;
        Ok(Self {
            active_relays: Arc::new(Semaphore::new(budgets.max_active_relays)),
            budgets,
        })
    }

    pub fn budgets(&self) -> &GatewayRelayBudgets {
        &self.budgets
    }

    pub fn try_begin_relay(&self) -> Result<AcceptedRelayPermit, GatewayRuntimeError> {
        let permit = self
            .active_relays
            .clone()
            .try_acquire_owned()
            .map_err(|_| {
                record_gateway_relay_guard(
                    "relay_overloaded",
                    "max_active_relays",
                    self.budgets.max_active_relays as u64,
                    None,
                );
                GatewayRuntimeError::RelayOverloaded {
                    max_active_relays: self.budgets.max_active_relays,
                }
            })?;
        Ok(AcceptedRelayPermit {
            budgets: self.budgets.clone(),
            permit,
            started_at: Instant::now(),
        })
    }
}

#[derive(Debug)]
pub struct AcceptedRelayPermit {
    budgets: GatewayRelayBudgets,
    permit: OwnedSemaphorePermit,
    started_at: Instant,
}

impl AcceptedRelayPermit {
    pub fn enforce_prebuffer_limit(&self, actual_bytes: usize) -> Result<(), GatewayRuntimeError> {
        if actual_bytes > self.budgets.max_relay_prebuffer_bytes {
            record_gateway_relay_guard(
                "relay_prebuffer_exceeded",
                "max_relay_prebuffer_bytes",
                self.budgets.max_relay_prebuffer_bytes as u64,
                Some(actual_bytes as u64),
            );
            return Err(GatewayRuntimeError::RelayPrebufferLimitExceeded {
                max_relay_prebuffer_bytes: self.budgets.max_relay_prebuffer_bytes,
                actual_bytes,
            });
        }
        Ok(())
    }

    pub fn enforce_idle_timeout(&self) -> Result<(), GatewayRuntimeError> {
        let elapsed = self.started_at.elapsed();
        if elapsed > self.budgets.relay_idle_timeout() {
            record_gateway_relay_guard(
                "relay_idle_timeout",
                "relay_idle_timeout_ms",
                self.budgets.relay_idle_timeout_ms,
                Some(elapsed.as_millis() as u64),
            );
            return Err(GatewayRuntimeError::RelayIdleTimeoutExceeded {
                relay_idle_timeout_ms: self.budgets.relay_idle_timeout_ms,
                elapsed_ms: elapsed.as_millis(),
            });
        }
        Ok(())
    }

    pub fn relay_idle_timeout(&self) -> StdDuration {
        self.budgets.relay_idle_timeout()
    }

    pub fn relay_permit(&self) -> &OwnedSemaphorePermit {
        &self.permit
    }
}

#[derive(Debug)]
pub struct ActiveRelayGuard<'a> {
    controller: &'a mut SessionController,
    relay_id: u64,
    _permit: AcceptedRelayPermit,
}

impl<'a> ActiveRelayGuard<'a> {
    pub fn acquire(
        controller: &'a mut SessionController,
        gate: &GatewayRelayGate,
        relay_id: u64,
    ) -> Result<Self, GatewayRuntimeError> {
        Ok(Self {
            controller,
            relay_id,
            _permit: gate.try_begin_relay()?,
        })
    }
}

impl Drop for ActiveRelayGuard<'_> {
    fn drop(&mut self) {
        self.controller.release_relay(self.relay_id);
    }
}

pub fn admit_client_hello(
    verifier: &SessionTokenVerifier,
    hello: &ClientHello,
    session_mode: SessionMode,
    datagram_mode: DatagramMode,
) -> Result<GatewayAdmissionOutcome, GatewayRuntimeError> {
    let token =
        std::str::from_utf8(&hello.token).map_err(|_| GatewayRuntimeError::TokenEncoding)?;
    let access = RequestedAccess {
        core_version: hello.max_version,
        carrier_profile_id: hello.carrier_profile_id.clone(),
        requested_capabilities: hello.requested_capabilities.clone(),
        manifest_id: hello.manifest_id.clone(),
        device_binding_id: hello.device_binding_id.clone(),
        session_mode,
    };
    let verified = verifier.verify(token, &access)?;

    let context = GatewayAdmissionContext {
        manifest_id: hello.manifest_id.clone(),
        device_binding_id: Some(hello.device_binding_id.as_str().to_owned()),
        allowed_core_versions: verified.claims.core_versions.clone(),
        allowed_capabilities: verified
            .claims
            .capabilities
            .iter()
            .map(|value| Capability::from_id(*value))
            .collect::<Result<Vec<_>, _>>()?,
        allowed_carrier_profiles: verified
            .claims
            .carrier_profiles
            .iter()
            .map(|value| ns_core::CarrierProfileId::new(value.clone()))
            .collect::<Result<Vec<_>, _>>()?,
    };
    context.validate_client_hello(hello)?;

    let mut controller = SessionController::new_gateway(verified.to_policy(SessionLimits {
        policy_epoch: verified.claims.policy_epoch,
        idle_timeout_ms: 30_000,
        session_lifetime_ms: 300_000,
        max_concurrent_relay_streams: 32,
        max_udp_flows: 8,
        max_udp_payload: 1200,
        datagram_mode,
        stats_mode: ns_core::StatsMode::Off,
    })?);
    let effective_limits = controller.policy.limits.clone();
    let response = ServerHello {
        selected_version: hello.max_version,
        session_id: SessionId::random(),
        server_nonce: [7_u8; 32],
        selected_capabilities: hello.requested_capabilities.clone(),
        policy_epoch: effective_limits.policy_epoch,
        effective_idle_timeout_ms: effective_limits.idle_timeout_ms,
        session_lifetime_ms: effective_limits.session_lifetime_ms,
        max_concurrent_relay_streams: effective_limits.max_concurrent_relay_streams,
        max_udp_flows: effective_limits.max_udp_flows,
        effective_max_udp_payload: effective_limits.max_udp_payload,
        datagram_mode: effective_limits.datagram_mode,
        stats_mode: effective_limits.stats_mode,
        server_metadata: Vec::new(),
    };
    controller.accept_hello(response.session_id);

    Ok(GatewayAdmissionOutcome {
        token: verified,
        controller,
        response,
    })
}

#[derive(Debug, Error)]
pub enum GatewayRuntimeError {
    #[error("pre-auth budget field {0} must be non-zero")]
    InvalidBudget(&'static str),
    #[error("gateway pre-auth budget exhausted ({max_pending_hellos} pending hellos)")]
    PreAuthOverloaded { max_pending_hellos: usize },
    #[error("control hello body exceeded {max_control_body_bytes} bytes (got {actual_bytes})")]
    ControlBodyTooLarge {
        max_control_body_bytes: usize,
        actual_bytes: usize,
    },
    #[error("handshake deadline of {handshake_deadline_ms}ms exceeded after {elapsed_ms}ms")]
    HandshakeDeadlineExceeded {
        handshake_deadline_ms: u64,
        elapsed_ms: u128,
    },
    #[error("gateway relay budget exhausted ({max_active_relays} active relays)")]
    RelayOverloaded { max_active_relays: usize },
    #[error("relay prebuffer exceeded {max_relay_prebuffer_bytes} bytes (got {actual_bytes})")]
    RelayPrebufferLimitExceeded {
        max_relay_prebuffer_bytes: usize,
        actual_bytes: usize,
    },
    #[error("relay idle timeout of {relay_idle_timeout_ms}ms exceeded after {elapsed_ms}ms")]
    RelayIdleTimeoutExceeded {
        relay_idle_timeout_ms: u64,
        elapsed_ms: u128,
    },
    #[error("hello token bytes were not valid UTF-8")]
    TokenEncoding,
    #[error("token verification failed: {0}")]
    Auth(#[from] ns_auth::AuthError),
    #[error("validation failed: {0}")]
    Validation(#[from] ns_core::ValidationError),
    #[error("policy derivation failed: {0}")]
    Policy(#[from] ns_policy::PolicyError),
    #[error("session admission failed: {0}")]
    Session(#[from] ns_session::SessionError),
}

impl GatewayRuntimeError {
    pub fn pre_auth_protocol_error_code(&self) -> Option<ProtocolErrorCode> {
        match self {
            Self::PreAuthOverloaded { .. } => Some(ProtocolErrorCode::RateLimited),
            Self::ControlBodyTooLarge { .. } => Some(ProtocolErrorCode::FrameTooLarge),
            Self::HandshakeDeadlineExceeded { .. } => Some(ProtocolErrorCode::IdleTimeout),
            Self::RelayOverloaded { .. } => Some(ProtocolErrorCode::FlowLimitReached),
            Self::RelayPrebufferLimitExceeded { .. } => Some(ProtocolErrorCode::FlowLimitReached),
            Self::RelayIdleTimeoutExceeded { .. } => Some(ProtocolErrorCode::IdleTimeout),
            _ => None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::future::Future;
    use std::io;
    use std::sync::{Arc, Mutex};
    use tracing_subscriber::fmt::MakeWriter;

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

    fn capture_logs<T>(run: impl FnOnce() -> T) -> (T, String) {
        let sink = TestLogSink::default();
        let subscriber = tracing_subscriber::fmt()
            .with_writer(sink.clone())
            .with_ansi(false)
            .without_time()
            .json()
            .finish();
        let dispatch = tracing::Dispatch::new(subscriber);
        let _guard = tracing::dispatcher::set_default(&dispatch);
        let result = run();
        drop(_guard);
        let bytes = sink.0.lock().expect("test log sink poisoned").clone();
        let output = String::from_utf8(bytes).expect("captured tracing output should be UTF-8");
        (result, output)
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
        let _guard = tracing::dispatcher::set_default(&dispatch);
        let result = future.await;
        drop(_guard);
        let bytes = sink.0.lock().expect("test log sink poisoned").clone();
        let output = String::from_utf8(bytes).expect("captured tracing output should be UTF-8");
        (result, output)
    }

    #[test]
    fn pre_auth_gate_enforces_pending_hello_limit() {
        let gate = GatewayPreAuthGate::new(GatewayPreAuthBudgets {
            max_pending_hellos: 1,
            max_control_body_bytes: 256,
            handshake_deadline_ms: 100,
        })
        .expect("budgets should be valid");

        let _permit = gate
            .try_begin_hello()
            .expect("first pending hello should be admitted");
        let error = gate
            .try_begin_hello()
            .expect_err("second pending hello should be rejected");

        assert!(matches!(
            error,
            GatewayRuntimeError::PreAuthOverloaded {
                max_pending_hellos: 1
            }
        ));
        assert_eq!(
            error.pre_auth_protocol_error_code(),
            Some(ProtocolErrorCode::RateLimited)
        );
    }

    #[test]
    fn pre_auth_gate_rejects_oversized_control_bodies() {
        let gate = GatewayPreAuthGate::new(GatewayPreAuthBudgets {
            max_pending_hellos: 1,
            max_control_body_bytes: 32,
            handshake_deadline_ms: 100,
        })
        .expect("budgets should be valid");
        let permit = gate
            .try_begin_hello()
            .expect("pending hello should be admitted");

        let error = permit
            .enforce_control_body_size(33)
            .expect_err("oversized control body should be rejected");
        assert!(matches!(
            error,
            GatewayRuntimeError::ControlBodyTooLarge {
                max_control_body_bytes: 32,
                actual_bytes: 33
            }
        ));
        assert_eq!(
            error.pre_auth_protocol_error_code(),
            Some(ProtocolErrorCode::FrameTooLarge)
        );
    }

    #[test]
    fn pre_auth_gate_rejects_expired_handshakes() {
        let gate = GatewayPreAuthGate::new(GatewayPreAuthBudgets {
            max_pending_hellos: 1,
            max_control_body_bytes: 256,
            handshake_deadline_ms: 1,
        })
        .expect("budgets should be valid");
        let permit = gate
            .try_begin_hello()
            .expect("pending hello should be admitted");

        std::thread::sleep(StdDuration::from_millis(5));
        let error = permit
            .enforce_handshake_deadline()
            .expect_err("expired handshake should be rejected");
        assert!(matches!(
            error,
            GatewayRuntimeError::HandshakeDeadlineExceeded {
                handshake_deadline_ms: 1,
                ..
            }
        ));
        assert_eq!(
            error.pre_auth_protocol_error_code(),
            Some(ProtocolErrorCode::IdleTimeout)
        );
    }

    #[test]
    fn relay_gate_rejects_overload_and_oversized_prebuffer() {
        let (_, logs) = capture_logs(|| {
            let gate = GatewayRelayGate::new(GatewayRelayBudgets {
                max_active_relays: 1,
                max_relay_prebuffer_bytes: 16,
                relay_idle_timeout_ms: 100,
            })
            .expect("relay budgets should be valid");

            let permit = gate
                .try_begin_relay()
                .expect("first relay should be admitted");
            let overload = gate
                .try_begin_relay()
                .expect_err("second relay should be rejected");
            assert!(matches!(
                overload,
                GatewayRuntimeError::RelayOverloaded {
                    max_active_relays: 1
                }
            ));
            assert_eq!(
                overload.pre_auth_protocol_error_code(),
                Some(ProtocolErrorCode::FlowLimitReached)
            );

            let prebuffer = permit
                .enforce_prebuffer_limit(32)
                .expect_err("oversized prebuffer should be rejected");
            assert!(matches!(
                prebuffer,
                GatewayRuntimeError::RelayPrebufferLimitExceeded {
                    max_relay_prebuffer_bytes: 16,
                    actual_bytes: 32
                }
            ));
            assert_eq!(
                prebuffer.pre_auth_protocol_error_code(),
                Some(ProtocolErrorCode::FlowLimitReached)
            );
        });

        assert!(logs.contains("\"event_name\":\"northstar.gateway.relay.guard\""));
        assert!(logs.contains("\"reason\":\"relay_overloaded\""));
        assert!(logs.contains("\"reason\":\"relay_prebuffer_exceeded\""));
    }

    #[tokio::test(flavor = "current_thread")]
    async fn relay_gate_emits_idle_timeout_observability_event() {
        let (error, logs) = capture_logs_async(async {
            let gate = GatewayRelayGate::new(GatewayRelayBudgets {
                max_active_relays: 1,
                max_relay_prebuffer_bytes: 16,
                relay_idle_timeout_ms: 5,
            })
            .expect("relay budgets should be valid");
            let permit = gate
                .try_begin_relay()
                .expect("relay should be admitted before timeout elapses");
            tokio::time::sleep(StdDuration::from_millis(15)).await;
            permit
                .enforce_idle_timeout()
                .expect_err("idle relay should emit a timeout error")
        })
        .await;

        assert!(matches!(
            error,
            GatewayRuntimeError::RelayIdleTimeoutExceeded {
                relay_idle_timeout_ms: 5,
                ..
            }
        ));
        assert_eq!(
            error.pre_auth_protocol_error_code(),
            Some(ProtocolErrorCode::IdleTimeout)
        );
        assert!(logs.contains("\"event_name\":\"northstar.gateway.relay.guard\""));
        assert!(logs.contains("\"reason\":\"relay_idle_timeout\""));
    }

    #[test]
    fn active_relay_guard_releases_registered_relays_when_dropped() {
        let gate = GatewayRelayGate::new(GatewayRelayBudgets {
            max_active_relays: 1,
            max_relay_prebuffer_bytes: 16,
            relay_idle_timeout_ms: 100,
        })
        .expect("relay budgets should be valid");
        let mut controller = SessionController::new_gateway(
            ns_policy::EffectiveSessionPolicy::tcp_and_udp_defaults(1),
        );
        controller.accept_hello(SessionId::random());
        controller.active_relays.insert(7);

        {
            let _guard = ActiveRelayGuard::acquire(&mut controller, &gate, 7)
                .expect("relay guard should acquire");
        }

        assert!(!controller.release_relay(7));
    }
}
