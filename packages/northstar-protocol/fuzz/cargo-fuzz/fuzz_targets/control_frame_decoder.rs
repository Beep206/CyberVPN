#![no_main]

use libfuzzer_sys::fuzz_target;
use ns_wire::FrameCodec;

fuzz_target!(|data: &[u8]| {
    let _ = FrameCodec::decode(data);
});
