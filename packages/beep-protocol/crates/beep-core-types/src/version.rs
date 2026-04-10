//! Protocol version for the Beep session core.

/// Identifies the wire semantics and capability set of a session core instance.
///
/// Versions are monotonically increasing. Each version defines a complete
/// set of mandatory frame types, error codes, and negotiation rules.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
#[derive(serde::Serialize, serde::Deserialize)]
pub struct CoreVersion(pub u32);

impl CoreVersion {
    /// Beep session core v1 — initial release.
    pub const V1: Self = Self(1);

    /// Returns the raw version number.
    pub const fn as_u32(self) -> u32 {
        self.0
    }
}

impl std::fmt::Display for CoreVersion {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "v{}", self.0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn version_display() {
        assert_eq!(CoreVersion::V1.to_string(), "v1");
        assert_eq!(CoreVersion(42).to_string(), "v42");
    }

    #[test]
    fn version_ordering() {
        assert!(CoreVersion::V1 < CoreVersion(2));
    }
}
