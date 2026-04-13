#![no_main]

use libfuzzer_sys::fuzz_target;
use ns_manifest::ManifestDocument;

fuzz_target!(|data: &[u8]| {
    if let Ok(input) = std::str::from_utf8(data) {
        let _ = ManifestDocument::parse_json(input);
    }
});
