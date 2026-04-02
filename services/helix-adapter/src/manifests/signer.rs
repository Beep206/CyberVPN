use base64::{engine::general_purpose::STANDARD_NO_PAD, Engine as _};
use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, SECRET_KEY_LENGTH};
use sha2::{Digest, Sha256};

use crate::{
    error::AppError,
    manifests::model::{
        ManifestDocument, ManifestIntegrity, ManifestSignature, UnsignedManifestDocument,
    },
};

#[derive(Debug, Clone)]
pub struct ManifestSigner {
    key_id: String,
    signing_key: SigningKey,
}

impl ManifestSigner {
    pub fn new(secret_key_base64: &str, key_id: &str) -> Result<Self, AppError> {
        let secret_key = STANDARD_NO_PAD
            .decode(secret_key_base64)
            .map_err(|error| AppError::Config(format!("invalid manifest signing key: {error}")))?;

        let secret_key: [u8; SECRET_KEY_LENGTH] = secret_key
            .try_into()
            .map_err(|_| AppError::Config("manifest signing key must be 32 bytes".to_string()))?;

        Ok(Self {
            key_id: key_id.to_string(),
            signing_key: SigningKey::from_bytes(&secret_key),
        })
    }

    pub fn key_id(&self) -> &str {
        &self.key_id
    }

    pub fn sign_bytes(&self, payload: &[u8]) -> Result<(String, ManifestSignature), AppError> {
        let manifest_hash = format!("sha256:{:x}", Sha256::digest(payload));
        let signature = self.signing_key.sign(payload);

        Ok((
            manifest_hash,
            ManifestSignature {
                alg: "ed25519",
                key_id: self.key_id.clone(),
                sig: STANDARD_NO_PAD.encode(signature.to_bytes()),
            },
        ))
    }

    pub fn verify_bytes(
        &self,
        payload: &[u8],
        expected_hash: &str,
        signature: &ManifestSignature,
    ) -> Result<(), AppError> {
        let actual_hash = format!("sha256:{:x}", Sha256::digest(payload));
        if expected_hash != actual_hash {
            return Err(AppError::Internal(
                "manifest hash does not match signed payload".to_string(),
            ));
        }

        let signature_bytes = STANDARD_NO_PAD
            .decode(&signature.sig)
            .map_err(|error| AppError::Internal(format!("invalid manifest signature: {error}")))?;
        let signature = Signature::try_from(signature_bytes.as_slice())
            .map_err(|error| AppError::Internal(format!("invalid signature bytes: {error}")))?;

        self.signing_key
            .verifying_key()
            .verify(payload, &signature)
            .map_err(|error| AppError::Internal(format!("signature verification failed: {error}")))
    }

    pub fn sign_manifest(
        &self,
        unsigned_manifest: UnsignedManifestDocument,
    ) -> Result<ManifestDocument, AppError> {
        let payload = serde_json::to_vec(&unsigned_manifest)?;
        let (manifest_hash, signature) = self.sign_bytes(&payload)?;

        Ok(ManifestDocument {
            schema_version: unsigned_manifest.schema_version,
            manifest_id: unsigned_manifest.manifest_id,
            rollout_id: unsigned_manifest.rollout_id,
            issued_at: unsigned_manifest.issued_at,
            expires_at: unsigned_manifest.expires_at,
            subject: unsigned_manifest.subject,
            transport: unsigned_manifest.transport,
            transport_profile: unsigned_manifest.transport_profile,
            compatibility_window: unsigned_manifest.compatibility_window,
            capability_profile: unsigned_manifest.capability_profile,
            routes: unsigned_manifest.routes,
            credentials: unsigned_manifest.credentials,
            integrity: ManifestIntegrity {
                manifest_hash,
                signature,
            },
            observability: unsigned_manifest.observability,
        })
    }

    pub fn verify_manifest(&self, manifest: &ManifestDocument) -> Result<(), AppError> {
        let unsigned = UnsignedManifestDocument {
            schema_version: manifest.schema_version,
            manifest_id: manifest.manifest_id,
            rollout_id: manifest.rollout_id.clone(),
            issued_at: manifest.issued_at,
            expires_at: manifest.expires_at,
            subject: manifest.subject.clone(),
            transport: manifest.transport.clone(),
            transport_profile: manifest.transport_profile.clone(),
            compatibility_window: manifest.compatibility_window.clone(),
            capability_profile: manifest.capability_profile.clone(),
            routes: manifest.routes.clone(),
            credentials: manifest.credentials.clone(),
            observability: manifest.observability.clone(),
        };

        let payload = serde_json::to_vec(&unsigned)?;
        self.verify_bytes(
            &payload,
            &manifest.integrity.manifest_hash,
            &manifest.integrity.signature,
        )
    }
}
