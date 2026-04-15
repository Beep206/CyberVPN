use std::fs;
use std::path::{Path, PathBuf};

fn workspace_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .canonicalize()
        .expect("workspace root should resolve from crate tests")
}

pub fn fixture_path(relative: &str) -> PathBuf {
    workspace_root().join(relative)
}

pub fn read_text_fixture(relative: &str) -> String {
    fs::read_to_string(fixture_path(relative))
        .unwrap_or_else(|error| panic!("failed to read fixture {relative}: {error}"))
}

pub fn read_binary_fixture(relative: &str) -> Vec<u8> {
    fs::read(fixture_path(relative))
        .unwrap_or_else(|error| panic!("failed to read fixture {relative}: {error}"))
}
