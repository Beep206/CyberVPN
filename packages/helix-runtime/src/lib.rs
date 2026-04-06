pub mod client;
pub mod crypto;
pub mod error;
pub mod model;
pub mod server;

pub use client::{spawn_client, ClientHandle, ClientStream, ClientStreamWriter};
pub use error::TransportError;
pub use model::{
    ClientConfig, ControlFrame, ServerConfig, ServerSnapshot, SessionSnapshot, StreamTarget,
    TransportRoute, PROTOCOL_MAGIC, PROTOCOL_VERSION,
};
pub use server::{spawn_server, ServerHandle};
