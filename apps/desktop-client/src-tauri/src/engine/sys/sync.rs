use crate::engine::error::AppError;
use aes_gcm::{
    aead::{Aead, AeadCore, KeyInit, OsRng},
    Aes256Gcm, Nonce,
};
use argon2::{
    password_hash::{rand_core::OsRng as ArgonRng, SaltString},
    Argon2, Params,
};
use keyring::Entry;
use serde::{Deserialize, Serialize};
use std::time::Duration;
use tauri::Manager;
use tokio::fs;

const NONCE_SIZE: usize = 12; // 96-bits

#[derive(Serialize, Deserialize)]
struct EncryptedPayload {
    salt: String,
    nonce: String,
    ciphertext: String,
}

// Ensure the local dev mock server works, or we mock the exact push/pull completely locally
// as per the user's approval in the implementation plan.
const MOCK_CLOUD_API_URL: &str = "https://mock-sync.cybervpn.com/api/v1/sync";

// Derives a 32-byte (256-bit) key from the given password and salt using Argon2id
fn derive_key(password: &str, salt: &SaltString) -> Result<[u8; 32], AppError> {
    let params = Params::new(19456, 2, 1, None).map_err(|error| {
        AppError::System(format!("Failed to initialize Argon2 parameters: {error}"))
    })?;
    let argon2 = Argon2::new(
        argon2::Algorithm::Argon2id,
        argon2::Version::V0x13,
        params, // secure baseline params
    );

    let mut key = [0u8; 32];
    let password_bytes = password.as_bytes();

    argon2
        .hash_password_into(password_bytes, salt.as_str().as_bytes(), &mut key)
        .map_err(|e| AppError::DecryptionFailed(format!("Key derivation failed: {}", e)))?;

    Ok(key)
}

fn encrypt_data(password: &str, plaintext: &[u8]) -> Result<String, AppError> {
    // Generate salt for Argon2
    let salt = SaltString::generate(&mut ArgonRng);
    let key_bytes = derive_key(password, &salt)?;
    let key = aes_gcm::Key::<Aes256Gcm>::from_slice(&key_bytes);

    // Initialize cipher
    let cipher = Aes256Gcm::new(key);

    // Generate 96-bit nonce
    let nonce = Aes256Gcm::generate_nonce(&mut OsRng); // 96-bits; unique per message

    // Encrypt
    let ciphertext = cipher
        .encrypt(&nonce, plaintext)
        .map_err(|e| AppError::System(format!("Encryption failed: {}", e)))?;

    // Encode payload manually using base64 for transit
    use base64::{engine::general_purpose::STANDARD as BASE64, Engine};

    let payload = EncryptedPayload {
        salt: salt.as_str().to_string(),
        nonce: BASE64.encode(nonce),
        ciphertext: BASE64.encode(ciphertext),
    };

    serde_json::to_string(&payload)
        .map_err(|e| AppError::System(format!("Payload serialization failed: {}", e)))
}

fn decrypt_data(password: &str, encrypted_json: &str) -> Result<Vec<u8>, AppError> {
    use base64::{engine::general_purpose::STANDARD as BASE64, Engine};

    let payload: EncryptedPayload = serde_json::from_str(encrypted_json)
        .map_err(|_| AppError::DecryptionFailed("Invalid payload format".into()))?;

    let salt = SaltString::from_b64(&payload.salt)
        .map_err(|_| AppError::DecryptionFailed("Invalid salt format".into()))?;

    let key_bytes = derive_key(password, &salt)?;
    let key = aes_gcm::Key::<Aes256Gcm>::from_slice(&key_bytes);
    let cipher = Aes256Gcm::new(key);

    let nonce_bytes = BASE64
        .decode(&payload.nonce)
        .map_err(|_| AppError::DecryptionFailed("Invalid nonce format".into()))?;

    if nonce_bytes.len() != NONCE_SIZE {
        return Err(AppError::DecryptionFailed("Invalid nonce length".into()));
    }

    let nonce = Nonce::from_slice(&nonce_bytes);
    let ciphertext = BASE64
        .decode(&payload.ciphertext)
        .map_err(|_| AppError::DecryptionFailed("Invalid ciphertext format".into()))?;

    let plaintext = cipher.decrypt(nonce, ciphertext.as_ref()).map_err(|_| {
        AppError::DecryptionFailed("Incorrect Sync Password or Corrupted Data".into())
    })?;

    Ok(plaintext)
}

fn get_service_keyring() -> Result<Entry, AppError> {
    Entry::new("CyberVPN_CloudSync", "sync_password")
        .map_err(|e| AppError::System(format!("Failed to access native Keyring: {}", e)))
}

#[tauri::command]
pub fn save_sync_password(password: String) -> Result<(), AppError> {
    let entry = get_service_keyring()?;
    entry
        .set_password(&password)
        .map_err(|e| AppError::System(format!("Failed to save Sync Password: {}", e)))?;
    Ok(())
}

#[tauri::command]
pub fn get_sync_password() -> Result<String, AppError> {
    let entry = get_service_keyring()?;
    entry
        .get_password()
        .map_err(|_| AppError::System("Sync Password not found".into()))
}

#[tauri::command]
pub fn delete_sync_password() -> Result<(), AppError> {
    let entry = get_service_keyring()?;
    let _ = entry.delete_credential(); // Ignore error if it doesn't exist
    Ok(())
}

// MOCK: In a real app we'd push to Supabase/PostgreSQL. Here we mock a successful API call
// by just writing the encrypted payload to a local "mock_cloud.json" to simulate remote server storage.
#[tauri::command]
pub async fn cloud_push(password: String, app_handle: tauri::AppHandle) -> Result<(), AppError> {
    if !crate::engine::store::get_store_path(&app_handle)?.exists() {
        return Err(AppError::System("No local data to sync".into()));
    }
    // Loading first completes any one-time plaintext subscription migration;
    // serializing the typed store guarantees bearer URLs are not synced.
    let store = crate::engine::store::load_store(&app_handle)?;
    let plaintext = serde_json::to_vec(&store)?;

    // CPU-intensive AES-GCM and Argon2 should run on the blocking threadpool
    let encrypted_payload =
        tokio::task::spawn_blocking(move || encrypt_data(&password, &plaintext))
            .await
            .map_err(|_| AppError::System("Encryption thread panicked".into()))??;

    // Simulate Network Request with timeout using tokio::select!
    let mock_network_call = async {
        // Sleep to simulate network latency
        tokio::time::sleep(Duration::from_millis(800)).await;

        let mut mock_cloud_path = app_handle
            .path()
            .app_data_dir()
            .map_err(|e| AppError::System(format!("Failed to get app data dir: {}", e)))?;
        mock_cloud_path.push("mock_cloud.json");

        fs::write(mock_cloud_path, encrypted_payload)
            .await
            .map_err(|e| AppError::CloudUnreachable(format!("Mock push failed: {}", e)))?;

        Ok::<(), AppError>(())
    };

    tokio::select! {
        res = mock_network_call => res,
        _ = tokio::time::sleep(Duration::from_secs(10)) => {
            Err(AppError::CloudUnreachable("Cloud Sync Push Timed Out. Network dead.".into()))
        }
    }
}

fn parse_secret_free_cloud_store(
    plaintext: &[u8],
) -> Result<crate::engine::store::AppDataStore, AppError> {
    let imported: crate::engine::store::AppDataStore =
        serde_json::from_slice(plaintext).map_err(|_| {
            AppError::SyncConflict(
                "Downloaded Cloud data is corrupted or invalid. Swap aborted.".into(),
            )
        })?;
    if imported
        .subscriptions
        .iter()
        .any(|subscription| subscription.legacy_url.is_some())
    {
        return Err(AppError::SyncConflict(
            "Cloud data contains legacy subscription credentials; migrate and re-sync it from the source device"
                .into(),
        ));
    }
    Ok(imported)
}

#[tauri::command]
pub async fn cloud_pull(password: String, app_handle: tauri::AppHandle) -> Result<(), AppError> {
    // Capture before network/decryption so any local command that commits
    // while the pull is in flight makes the final replacement fail closed.
    let expected_local_revision = crate::engine::store::load_store(&app_handle)?.store_revision;
    // Simulate Network Request with timeout
    let mock_network_call = async {
        tokio::time::sleep(Duration::from_millis(600)).await;

        let mut mock_cloud_path = app_handle
            .path()
            .app_data_dir()
            .map_err(|e| AppError::System(format!("Failed to get app data dir: {}", e)))?;
        mock_cloud_path.push("mock_cloud.json");

        if !mock_cloud_path.exists() {
            return Err(AppError::SyncConflict(
                "No data exists in the cloud to pull.".into(),
            ));
        }

        let data = fs::read_to_string(mock_cloud_path)
            .await
            .map_err(|e| AppError::CloudUnreachable(format!("Mock pull failed: {}", e)))?;

        Ok::<String, AppError>(data)
    };

    let encrypted_payload = tokio::select! {
        res = mock_network_call => res?,
        _ = tokio::time::sleep(Duration::from_secs(10)) => {
            return Err(AppError::CloudUnreachable("Cloud Sync Pull Timed Out. Network dead.".into()));
        }
    };

    // CPU-intensive decrypt offloaded
    let plaintext =
        tokio::task::spawn_blocking(move || decrypt_data(&password, &encrypted_payload))
            .await
            .map_err(|_| AppError::System("Decryption thread panicked".into()))??;

    let imported = parse_secret_free_cloud_store(&plaintext)?;

    // Re-serialize the typed, secret-free model through the store's durable
    // atomic replacement instead of ever writing decrypted raw bytes to disk.
    crate::engine::store::replace_store_if_revision_atomic(
        &app_handle,
        &imported,
        expected_local_revision,
    )?;

    Ok(())
}

#[tauri::command]
pub fn generate_pairing_qr(password: String) -> Result<String, AppError> {
    use base64::{engine::general_purpose::STANDARD as BASE64, Engine};

    // In a real scenario, this contains the Cloud User ID/Token and the ephemeral sync password
    let payload = format!(
        "cybervpn://sync?endpoint={}&key={}",
        MOCK_CLOUD_API_URL, password
    );
    let b64_payload = BASE64.encode(payload);

    Ok(b64_payload)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cloud_import_rejects_plaintext_subscription_credentials_without_echoing_them() {
        let mut value = serde_json::to_value(crate::engine::store::AppDataStore::default())
            .expect("default store must serialize");
        value["subscriptions"] = serde_json::json!([{
            "id": "b831381d-6324-4d53-ad4f-8cda48b30811",
            "name": "Primary",
            "url": "https://203.0.114.1/cloud-bearer-token",
            "autoUpdate": true,
            "lastUpdated": null
        }]);
        let bytes = serde_json::to_vec(&value).expect("fixture must serialize");

        let error = parse_secret_free_cloud_store(&bytes)
            .err()
            .expect("cloud payloads must never import plaintext subscription URLs");

        assert!(error
            .to_string()
            .contains("legacy subscription credentials"));
        assert!(!error.to_string().contains("cloud-bearer-token"));
    }
}
