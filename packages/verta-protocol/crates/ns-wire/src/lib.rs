#![forbid(unsafe_code)]

mod codec;
mod types;

pub use codec::{
    FrameCodec, WireError, decode_udp_datagram, decode_varint, encode_udp_datagram, encode_varint,
};
pub use types::{
    ClientHello, DatagramFlags, ErrorFrame, FlowFlags, Frame, FrameType, MetadataTlv, OpenFlags,
    Ping, Pong, ServerHello, SessionClose, StreamAccept, StreamOpen, StreamReject, TargetAddress,
    UdpDatagram, UdpFlowClose, UdpFlowOk, UdpFlowOpen, UdpStreamAccept, UdpStreamClose,
    UdpStreamOpen, UdpStreamPacket,
};
