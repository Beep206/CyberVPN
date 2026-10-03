//! Connection keepalive and reconnect pacing for the Beep runtime.
//!
//! A long-lived tunnel needs two things the raw session core does not provide:
//!
//! - a periodic liveness beacon so idle connections stay warm and a dead peer
//!   is noticed (sent as a `HEALTH_SUMMARY` frame, which is an ignorable
//!   telemetry frame the peer already tolerates), and
//! - an idle deadline after which the session is declared dead so the client
//!   can reconnect.
//!
//! The concrete intervals are expected to come from the signed transport
//! profile in a later stage; [`KeepaliveConfig::default`] gives conservative
//! fallbacks for now.

use std::time::Duration;

/// Keepalive timing for a session.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct KeepaliveConfig {
    /// How often to send a liveness beacon.
    pub interval: Duration,
    /// How long without any received frame before the session is dead.
    pub idle_timeout: Duration,
}

impl Default for KeepaliveConfig {
    fn default() -> Self {
        Self {
            interval: Duration::from_secs(15),
            idle_timeout: Duration::from_secs(45),
        }
    }
}

impl KeepaliveConfig {
    /// Validate that the idle timeout leaves room for at least two beacons.
    pub fn is_sane(&self) -> bool {
        !self.interval.is_zero()
            && !self.idle_timeout.is_zero()
            && self.idle_timeout >= self.interval * 2
    }
}

/// Reconnect backoff with full jitter.
///
/// Returns a delay drawn uniformly from `[0, capped_exponential]`, where the
/// exponential is `base * 2^attempt` clamped to `cap`. Full jitter avoids
/// reconnect storms when many clients drop at once. `attempt` is zero-based.
///
/// `rand01` must be a value in `[0, 1)`; the caller supplies it so the policy
/// stays deterministic and testable.
pub fn reconnect_delay(attempt: u32, base: Duration, cap: Duration, rand01: f64) -> Duration {
    let ceiling = capped_exponential(attempt, base, cap);
    let frac = rand01.clamp(0.0, 1.0);
    ceiling.mul_f64(frac)
}

/// The capped exponential ceiling `min(cap, base * 2^attempt)`.
pub fn capped_exponential(attempt: u32, base: Duration, cap: Duration) -> Duration {
    let cap_nanos = cap.as_nanos();
    // base * 2^attempt in nanoseconds, saturating on shift overflow.
    let scaled = base.as_nanos().checked_shl(attempt).unwrap_or(u128::MAX);
    if scaled >= cap_nanos {
        cap
    } else {
        Duration::from_nanos(scaled as u64)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_config_is_sane() {
        assert!(KeepaliveConfig::default().is_sane());
    }

    #[test]
    fn insane_configs_rejected() {
        assert!(!KeepaliveConfig {
            interval: Duration::ZERO,
            idle_timeout: Duration::from_secs(45),
        }
        .is_sane());
        assert!(!KeepaliveConfig {
            interval: Duration::from_secs(30),
            idle_timeout: Duration::from_secs(45), // less than 2x interval
        }
        .is_sane());
    }

    #[test]
    fn capped_exponential_grows_then_caps() {
        let base = Duration::from_millis(500);
        let cap = Duration::from_secs(30);
        assert_eq!(capped_exponential(0, base, cap), Duration::from_millis(500));
        assert_eq!(capped_exponential(1, base, cap), Duration::from_secs(1));
        assert_eq!(capped_exponential(2, base, cap), Duration::from_secs(2));
        assert_eq!(capped_exponential(6, base, cap), Duration::from_secs(30)); // 32s -> capped
        assert_eq!(capped_exponential(60, base, cap), cap); // no overflow
    }

    #[test]
    fn jitter_stays_within_ceiling() {
        let base = Duration::from_secs(1);
        let cap = Duration::from_secs(30);
        for attempt in 0..8 {
            let ceiling = capped_exponential(attempt, base, cap);
            for r in [0.0, 0.5, 0.999] {
                let d = reconnect_delay(attempt, base, cap, r);
                assert!(d <= ceiling, "delay {d:?} exceeded ceiling {ceiling:?}");
            }
        }
        // Full jitter can return (near) zero and (near) the ceiling.
        assert_eq!(reconnect_delay(3, base, cap, 0.0), Duration::ZERO);
    }
}
