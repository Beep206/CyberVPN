use std::io;

/// Represents an abstract mechanism to modify the OS routing table.
#[async_trait::async_trait]
pub trait OsRouter: Send + Sync {
    /// Add a route to the OS routing table pointing to the VPN interface.
    /// `cidr` is a network string like "192.168.10.0/24".
    async fn add_route(&mut self, cidr: &str) -> io::Result<()>;

    /// Remove a route from the OS routing table.
    async fn remove_route(&mut self, cidr: &str) -> io::Result<()>;
}

/// A BGP Client Skeleton for dynamic split tunneling.
/// 
/// This client would typically connect to a BGP Daemon (like bird/frr)
/// or implement basic BGP peer polling to receive dynamic route announcements.
pub struct BgpRouteManager<R: OsRouter> {
    router: R,
}

impl<R: OsRouter> BgpRouteManager<R> {
    pub fn new(router: R) -> Self {
        Self { router }
    }

    /// Announce a new CIDR locally by updating the OS table.
    pub async fn apply_bgp_route(&mut self, cidr: &str) -> io::Result<()> {
        self.router.add_route(cidr).await
    }

    /// Withdraw a local CIDR announcement.
    pub async fn withdraw_bgp_route(&mut self, cidr: &str) -> io::Result<()> {
        self.router.remove_route(cidr).await
    }

    /// Background task that listens for BGP events on a unix socket or internal channel
    /// and dynamically modifies the `router`.
    pub async fn run_bgp_listener(&mut self) -> io::Result<()> {
        // [To be implemented: Connect to BGP demon / ingest ExaBGP JSON messages]
        // loop { ... self.apply_bgp_route(...).await? ... }
        Ok(())
    }
}
