#![no_main]

use libfuzzer_sys::fuzz_target;
use ns_wire::decode_udp_datagram;

fuzz_target!(|data: &[u8]| {
    let _ = decode_udp_datagram(data);
});
