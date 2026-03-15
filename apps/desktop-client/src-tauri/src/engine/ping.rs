use crate::engine::error::AppError;
use crate::ipc::models::ProxyNode;
use std::time::Duration;
use tokio::net::TcpStream;
use tokio::time::timeout;

pub async fn test_latency(node: &ProxyNode) -> Result<u32, AppError> {
    if node.server.is_empty() || node.port == 0 {
        return Err(AppError::System("Invalid server address or port".to_string()));
    }

    let address = format!("{}:{}", node.server, node.port);
    let start_time = std::time::Instant::now();

    // 3000ms max timeout for TCP handshake
    match timeout(Duration::from_millis(3000), TcpStream::connect(&address)).await {
        Ok(Ok(_stream)) => {
            let elapsed = start_time.elapsed().as_millis() as u32;
            Ok(elapsed)
        }
        Ok(Err(e)) => Err(AppError::System(format!("Connection failed: {}", e))),
        Err(_) => Err(AppError::System("Connection timed out".to_string())),
    }
}
