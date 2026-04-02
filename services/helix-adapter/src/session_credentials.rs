use base64::{engine::general_purpose::STANDARD_NO_PAD, Engine as _};
use sha2::{Digest, Sha256};

pub fn derive_rollout_session_token(
    rollout_id: &str,
    transport_profile_id: &str,
    key_id: &str,
) -> String {
    let digest = Sha256::digest(format!(
        "helix-session:{rollout_id}:{transport_profile_id}:{key_id}:v1"
    ));
    format!("pts_{}", STANDARD_NO_PAD.encode(digest))
}
