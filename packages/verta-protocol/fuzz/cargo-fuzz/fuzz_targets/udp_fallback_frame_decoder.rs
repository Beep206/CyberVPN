#![no_main]

use libfuzzer_sys::fuzz_target;
use ns_wire::{Frame, FrameCodec};

fuzz_target!(|data: &[u8]| {
    if let Ok(frame) = FrameCodec::decode(data) {
        match frame {
            Frame::UdpStreamOpen(_)
            | Frame::UdpStreamAccept(_)
            | Frame::UdpStreamPacket(_)
            | Frame::UdpStreamClose(_) => {}
            _ => {}
        }
    }
});
