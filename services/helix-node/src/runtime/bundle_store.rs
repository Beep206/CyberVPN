use std::path::{Path, PathBuf};

use tokio::fs;

use crate::{
    control_plane::client::NodeAssignmentDocument, error::AppError, state::NodeRuntimeSnapshot,
};

#[derive(Debug, Clone)]
pub struct BundleStore {
    root_dir: PathBuf,
}

impl BundleStore {
    pub async fn new(root_dir: PathBuf) -> Result<Self, AppError> {
        let store = Self { root_dir };
        store.ensure_layout().await?;
        Ok(store)
    }

    pub async fn ensure_layout(&self) -> Result<(), AppError> {
        fs::create_dir_all(self.assignments_dir()).await?;
        Ok(())
    }

    pub async fn stage_assignment(
        &self,
        assignment: &NodeAssignmentDocument,
    ) -> Result<(), AppError> {
        self.write_json_atomically(
            &self.assignment_path(&assignment.runtime_profile.bundle_version),
            assignment,
        )
        .await
    }

    pub async fn bundle_exists(&self, bundle_version: &str) -> Result<bool, AppError> {
        Ok(fs::try_exists(self.assignment_path(bundle_version)).await?)
    }

    pub async fn load_assignment(
        &self,
        bundle_version: &str,
    ) -> Result<Option<NodeAssignmentDocument>, AppError> {
        let path = self.assignment_path(bundle_version);
        if !fs::try_exists(&path).await? {
            return Ok(None);
        }

        let payload = fs::read_to_string(path).await?;
        serde_json::from_str(&payload)
            .map(Some)
            .map_err(AppError::Json)
    }

    pub async fn save_snapshot(&self, snapshot: &NodeRuntimeSnapshot) -> Result<(), AppError> {
        self.write_json_atomically(&self.snapshot_path(), snapshot)
            .await
    }

    pub async fn load_snapshot(&self) -> Result<Option<NodeRuntimeSnapshot>, AppError> {
        let path = self.snapshot_path();
        if !fs::try_exists(&path).await? {
            return Ok(None);
        }

        let payload = fs::read_to_string(path).await?;
        serde_json::from_str(&payload)
            .map(Some)
            .map_err(AppError::Json)
    }

    fn assignments_dir(&self) -> PathBuf {
        self.root_dir.join("assignments")
    }

    fn assignment_path(&self, bundle_version: &str) -> PathBuf {
        self.assignments_dir()
            .join(format!("{}.json", safe_file_name(bundle_version)))
    }

    fn snapshot_path(&self) -> PathBuf {
        self.root_dir.join("runtime-state.json")
    }

    async fn write_json_atomically<T: serde::Serialize>(
        &self,
        path: &Path,
        payload: &T,
    ) -> Result<(), AppError> {
        let temp_path = path.with_extension("tmp");
        let serialized = serde_json::to_vec_pretty(payload)?;
        fs::write(&temp_path, serialized).await?;
        if fs::try_exists(path).await? {
            let _ = fs::remove_file(path).await;
        }
        fs::rename(&temp_path, path).await?;
        Ok(())
    }
}

fn safe_file_name(value: &str) -> String {
    value
        .chars()
        .map(|ch| match ch {
            '/' | '\\' | ':' | '*' | '?' | '"' | '<' | '>' | '|' => '_',
            other => other,
        })
        .collect()
}
