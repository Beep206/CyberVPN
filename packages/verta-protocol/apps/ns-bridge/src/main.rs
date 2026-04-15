use anyhow::Context;
use async_trait::async_trait;
use axum::serve;
use clap::{Parser, Subcommand, ValueEnum};
use ed25519_dalek::SigningKey;
use ed25519_dalek::pkcs8::{EncodePrivateKey, EncodePublicKey};
use ns_auth::SessionTokenSigner;
use ns_bridge_api::{BridgeHttpBudgets, BridgeHttpServiceState, build_bridge_router};
use ns_bridge_domain::{
    BridgeCarrierProfile, BridgeDomain, BridgeGatewayEndpoint, BridgeManifestContext,
    BridgeManifestTemplate,
};
use ns_manifest::{
    ClientConstraints, ConnectBackoff, DevicePolicy, HttpTemplate, HttpTemplateMethod,
    ManifestCarrierKind, ManifestSigner, RefreshMode, RefreshPolicy, RetryPolicy,
    RoutingFailoverMode, RoutingPolicy, RoutingSelectionMode, TelemetryPolicy, TokenService,
    ZeroRttPolicy,
};
use ns_observability::{
    init_tracing, record_bridge_store_backend_selected, record_bridge_store_service_health,
};
use ns_remnawave_adapter::{
    AccountLifecycle, AccountSnapshot, AdapterError, AdapterWebhookEffect, BootstrapSubject,
    HttpRemnawaveAdapter, HttpRemnawaveAdapterConfig, RemnawaveAdapter, VerifiedWebhookPayload,
    VertaAccess, WebhookAuthenticator, WebhookVerificationConfig, WebhookVerificationError,
};
use ns_storage::{
    FileBackedBridgeStore, HttpServiceBackedBridgeStoreAdapter, ServiceBackedBridgeStore,
    ServiceBackedBridgeStoreConfig, SharedBridgeStore, SqliteBridgeStore,
    build_service_backed_bridge_store_router,
};
use std::collections::BTreeMap;
use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::Arc;
use time::{Duration, OffsetDateTime};
use tokio::sync::oneshot;
use url::Url;

#[derive(Parser)]
#[command(name = "ns-bridge")]
struct Cli {
    #[arg(long, default_value_t = false)]
    json_logs: bool,
    #[arg(long, value_enum, default_value_t = StoreBackend::Sqlite)]
    store_backend: StoreBackend,
    #[arg(long)]
    state_path: Option<PathBuf>,
    #[arg(long)]
    service_store_endpoint: Option<String>,
    #[arg(long, default_value_t = 3_000)]
    service_store_timeout_ms: u64,
    #[arg(long)]
    service_store_auth_token: Option<String>,
    #[arg(long = "service-store-fallback-endpoint")]
    service_store_fallback_endpoints: Vec<String>,
    #[arg(long, value_enum, default_value_t = AdapterBackend::Fake)]
    remnawave_adapter_backend: AdapterBackend,
    #[arg(long)]
    remnawave_base_url: Option<String>,
    #[arg(long)]
    remnawave_api_token: Option<String>,
    #[arg(long, default_value_t = 3_000)]
    remnawave_request_timeout_ms: u64,
    #[command(subcommand)]
    command: Command,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, ValueEnum)]
enum StoreBackend {
    File,
    Sqlite,
    Service,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, ValueEnum)]
enum AdapterBackend {
    Fake,
    Http,
}

#[derive(Debug, Clone)]
struct BridgeStoreConfig {
    backend: StoreBackend,
    state_path: Option<PathBuf>,
    service_store_endpoint: Option<String>,
    service_store_timeout_ms: u64,
    service_store_auth_token: Option<String>,
    service_store_fallback_endpoints: Vec<String>,
}

#[derive(Debug, Clone)]
struct RemnawaveAdapterConfig {
    backend: AdapterBackend,
    base_url: Option<String>,
    api_token: Option<String>,
    request_timeout_ms: u64,
}

impl BridgeStoreConfig {
    fn resolved_state_path(&self) -> anyhow::Result<PathBuf> {
        match self.backend {
            StoreBackend::File => Ok(self
                .state_path
                .clone()
                .unwrap_or_else(|| PathBuf::from("var/ns-bridge/state.json"))),
            StoreBackend::Sqlite => Ok(self
                .state_path
                .clone()
                .unwrap_or_else(|| PathBuf::from("var/ns-bridge/state.sqlite3"))),
            StoreBackend::Service => anyhow::bail!(
                "service-backed bridge stores do not use --state-path; provide --service-store-endpoint instead"
            ),
        }
    }

    fn required_service_store_auth_token(&self) -> anyhow::Result<String> {
        let auth_token = self
            .service_store_auth_token
            .clone()
            .context(
                "remote/service bridge-store mode requires --service-store-auth-token for deployment use",
            )?;
        if auth_token.trim().is_empty() {
            anyhow::bail!(
                "remote/service bridge-store mode requires a non-empty --service-store-auth-token"
            );
        }
        Ok(auth_token)
    }

    fn service_config_for_endpoint(
        &self,
        endpoint: impl Into<String>,
    ) -> anyhow::Result<ServiceBackedBridgeStoreConfig> {
        self.service_config_for_endpoint_with_auth_token(
            endpoint,
            self.required_service_store_auth_token()?,
        )
    }

    fn service_config_for_endpoint_with_auth_token(
        &self,
        endpoint: impl Into<String>,
        auth_token: impl Into<String>,
    ) -> anyhow::Result<ServiceBackedBridgeStoreConfig> {
        ServiceBackedBridgeStoreConfig::new(endpoint, self.service_store_timeout_ms)?
            .with_auth_token(auth_token)
            .map_err(anyhow::Error::from)
    }

    fn service_config(&self) -> anyhow::Result<ServiceBackedBridgeStoreConfig> {
        let endpoint = self
            .service_store_endpoint
            .clone()
            .context("service-backed bridge stores require --service-store-endpoint")?;
        let mut config = self.service_config_for_endpoint(endpoint)?;
        for endpoint in &self.service_store_fallback_endpoints {
            config = config.with_fallback_endpoint(endpoint.clone())?;
        }
        Ok(config)
    }
}

impl RemnawaveAdapterConfig {
    fn build_http(&self) -> anyhow::Result<HttpRemnawaveAdapter> {
        let base_url = self
            .base_url
            .clone()
            .context("HTTP Remnawave adapter requires --remnawave-base-url")?;
        let api_token = self
            .api_token
            .clone()
            .context("HTTP Remnawave adapter requires --remnawave-api-token")?;
        let config = HttpRemnawaveAdapterConfig::new(base_url, api_token, self.request_timeout_ms)?;
        Ok(HttpRemnawaveAdapter::new(config))
    }
}

#[derive(Debug, Clone)]
struct BridgeServiceRuntimeConfig {
    listen: SocketAddr,
    budgets: BridgeHttpBudgets,
}

#[derive(Debug, Clone)]
struct BridgeStoreServiceRuntimeConfig {
    listen: SocketAddr,
}

#[derive(Debug, Clone)]
struct BridgeTopologyRuntimeConfig {
    public_listen: SocketAddr,
    store_listen: SocketAddr,
    budgets: BridgeHttpBudgets,
}

struct BridgeRuntime {
    listen: SocketAddr,
    router: axum::Router,
    store_backend: &'static str,
}

struct BridgeStoreRuntime {
    listen: SocketAddr,
    router: axum::Router,
    store_backend: &'static str,
}

struct ManagedServiceRuntime {
    endpoint: String,
    backend: &'static str,
    shutdown: Option<oneshot::Sender<()>>,
    task: tokio::task::JoinHandle<anyhow::Result<()>>,
}

struct BridgeTopologyRuntime {
    public: ManagedServiceRuntime,
    store: ManagedServiceRuntime,
}

impl ManagedServiceRuntime {
    fn request_shutdown(&mut self) {
        if let Some(shutdown) = self.shutdown.take() {
            let _ = shutdown.send(());
        }
    }

    async fn join(self) -> anyhow::Result<()> {
        let ManagedServiceRuntime { backend, task, .. } = self;
        match task.await {
            Ok(result) => result,
            Err(error) => {
                Err(anyhow::Error::new(error).context(format!("{} service task failed", backend)))
            }
        }
    }
}

impl BridgeTopologyRuntime {
    async fn wait(self) -> anyhow::Result<()> {
        tokio::try_join!(self.public.join(), self.store.join()).map(|_| ())
    }

    #[cfg(test)]
    async fn shutdown(mut self) -> anyhow::Result<()> {
        self.public.request_shutdown();
        self.store.request_shutdown();
        let public = self.public.join().await;
        let store = self.store.join().await;
        public?;
        store?;
        Ok(())
    }
}

impl Cli {
    fn store_config(&self) -> BridgeStoreConfig {
        BridgeStoreConfig {
            backend: self.store_backend,
            state_path: self.state_path.clone(),
            service_store_endpoint: self.service_store_endpoint.clone(),
            service_store_timeout_ms: self.service_store_timeout_ms,
            service_store_auth_token: self.service_store_auth_token.clone(),
            service_store_fallback_endpoints: self.service_store_fallback_endpoints.clone(),
        }
    }

    fn remnawave_adapter_config(&self) -> RemnawaveAdapterConfig {
        RemnawaveAdapterConfig {
            backend: self.remnawave_adapter_backend,
            base_url: self.remnawave_base_url.clone(),
            api_token: self.remnawave_api_token.clone(),
            request_timeout_ms: self.remnawave_request_timeout_ms,
        }
    }
}

#[derive(Subcommand)]
enum Command {
    Serve {
        #[arg(long, default_value = "127.0.0.1:8080")]
        listen: SocketAddr,
        #[arg(long, default_value_t = 16 * 1024)]
        max_json_body_bytes: usize,
        #[arg(long, default_value_t = 64 * 1024)]
        max_webhook_body_bytes: usize,
        #[arg(long, default_value = "sig-ok")]
        webhook_signature: String,
    },
    ServeStore {
        #[arg(long, default_value = "127.0.0.1:8081")]
        listen: SocketAddr,
    },
    ServeTopology {
        #[arg(long, default_value = "127.0.0.1:8080")]
        public_listen: SocketAddr,
        #[arg(long, default_value = "127.0.0.1:8081")]
        store_listen: SocketAddr,
        #[arg(long, default_value_t = 16 * 1024)]
        max_json_body_bytes: usize,
        #[arg(long, default_value_t = 64 * 1024)]
        max_webhook_body_bytes: usize,
        #[arg(long, default_value = "sig-ok")]
        webhook_signature: String,
    },
    CompileDemoManifest {
        #[arg(long)]
        generated_at_unix: Option<i64>,
    },
    PrintDemoManifestPublicKey,
}

struct StaticWebhookAuthenticator {
    expected_signature: String,
}

impl WebhookAuthenticator for StaticWebhookAuthenticator {
    fn verify(
        &self,
        _timestamp_header: &str,
        signature_header: &str,
        _body: &[u8],
    ) -> Result<(), WebhookVerificationError> {
        if signature_header == self.expected_signature {
            Ok(())
        } else {
            Err(WebhookVerificationError::InvalidSignature)
        }
    }
}

#[derive(Clone)]
struct RuntimeRemnawaveAdapter {
    inner: Arc<dyn RemnawaveAdapter>,
}

impl RuntimeRemnawaveAdapter {
    fn new<A>(adapter: A) -> Self
    where
        A: RemnawaveAdapter + 'static,
    {
        Self {
            inner: Arc::new(adapter),
        }
    }
}

#[async_trait]
impl RemnawaveAdapter for RuntimeRemnawaveAdapter {
    async fn resolve_bootstrap_subject(
        &self,
        subject: &BootstrapSubject,
    ) -> Result<AccountSnapshot, AdapterError> {
        self.inner.resolve_bootstrap_subject(subject).await
    }

    async fn fetch_account_snapshot(
        &self,
        account_id: &str,
    ) -> Result<AccountSnapshot, AdapterError> {
        self.inner.fetch_account_snapshot(account_id).await
    }

    async fn fetch_user_metadata(
        &self,
        account_id: &str,
    ) -> Result<Option<serde_json::Value>, AdapterError> {
        self.inner.fetch_user_metadata(account_id).await
    }

    async fn upsert_user_metadata(
        &self,
        account_id: &str,
        patch: serde_json::Value,
    ) -> Result<(), AdapterError> {
        self.inner.upsert_user_metadata(account_id, patch).await
    }

    async fn ingest_verified_webhook(
        &self,
        payload: VerifiedWebhookPayload,
    ) -> Result<AdapterWebhookEffect, AdapterError> {
        self.inner.ingest_verified_webhook(payload).await
    }
}

#[derive(Clone)]
struct RuntimeWebhookAuthenticator {
    inner: Arc<dyn WebhookAuthenticator>,
}

impl RuntimeWebhookAuthenticator {
    fn new<W>(authenticator: W) -> Self
    where
        W: WebhookAuthenticator + 'static,
    {
        Self {
            inner: Arc::new(authenticator),
        }
    }
}

impl WebhookAuthenticator for RuntimeWebhookAuthenticator {
    fn verify(
        &self,
        timestamp_header: &str,
        signature_header: &str,
        body: &[u8],
    ) -> Result<(), WebhookVerificationError> {
        self.inner.verify(timestamp_header, signature_header, body)
    }
}

struct BridgeRuntimeDependencies {
    adapter: RuntimeRemnawaveAdapter,
    manifest_template: BridgeManifestTemplate,
    manifest_signer: ManifestSigner,
    token_signer: SessionTokenSigner,
    webhook_authenticator: RuntimeWebhookAuthenticator,
    webhook_verification: WebhookVerificationConfig,
    session_token_ttl: Duration,
}

fn deployment_scope_label(scope: ns_storage::BridgeStoreDeploymentScope) -> &'static str {
    match scope {
        ns_storage::BridgeStoreDeploymentScope::LocalOnly => "local_only",
        ns_storage::BridgeStoreDeploymentScope::SharedDurable => "shared_durable",
    }
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();
    init_tracing("ns_bridge", cli.json_logs);
    let store_config = cli.store_config();
    let adapter_config = cli.remnawave_adapter_config();

    match cli.command {
        Command::Serve {
            listen,
            max_json_body_bytes,
            max_webhook_body_bytes,
            webhook_signature,
        } => {
            let store = open_shared_store(&store_config).await?;
            let dependencies = build_runtime_dependencies(&adapter_config, webhook_signature)?;
            let runtime = build_bridge_runtime(
                store,
                BridgeServiceRuntimeConfig {
                    listen,
                    budgets: BridgeHttpBudgets {
                        max_json_body_bytes,
                        max_webhook_body_bytes,
                    },
                },
                dependencies,
            )?;
            serve_bridge_runtime(runtime).await?;
        }
        Command::ServeStore { listen } => {
            let store = open_shared_store(&store_config).await?;
            let runtime = build_store_service_runtime(
                store,
                BridgeStoreServiceRuntimeConfig { listen },
                store_config.required_service_store_auth_token()?,
            )?;
            serve_store_runtime(runtime).await?;
        }
        Command::ServeTopology {
            public_listen,
            store_listen,
            max_json_body_bytes,
            max_webhook_body_bytes,
            webhook_signature,
        } => {
            let dependencies = build_runtime_dependencies(&adapter_config, webhook_signature)?;
            serve_bridge_topology(
                &store_config,
                BridgeTopologyRuntimeConfig {
                    public_listen,
                    store_listen,
                    budgets: BridgeHttpBudgets {
                        max_json_body_bytes,
                        max_webhook_body_bytes,
                    },
                },
                dependencies,
            )
            .await?;
        }
        Command::CompileDemoManifest { generated_at_unix } => {
            compile_demo_manifest(open_shared_store(&store_config).await?, generated_at_unix)
                .await?;
        }
        Command::PrintDemoManifestPublicKey => {
            let manifest_signing_key = SigningKey::from_bytes(&[13_u8; 32]);
            let public_pem = manifest_signing_key
                .verifying_key()
                .to_public_key_pem(Default::default())
                .context("failed to encode demo manifest public key")?;
            print!("{public_pem}");
        }
    }

    Ok(())
}

async fn open_shared_store(config: &BridgeStoreConfig) -> anyhow::Result<SharedBridgeStore> {
    let store = match config.backend {
        StoreBackend::File | StoreBackend::Sqlite => open_local_shared_store(config)?,
        StoreBackend::Service => open_service_backed_shared_store(config.service_config()?).await?,
    };

    record_bridge_store_backend_selected(
        store.backend_name(),
        deployment_scope_label(store.deployment_scope()),
    );
    Ok(store)
}

fn open_local_shared_store(config: &BridgeStoreConfig) -> anyhow::Result<SharedBridgeStore> {
    match config.backend {
        StoreBackend::File => Ok(SharedBridgeStore::new(FileBackedBridgeStore::open(
            config.resolved_state_path()?,
        )?)),
        StoreBackend::Sqlite => Ok(SharedBridgeStore::new(SqliteBridgeStore::open(
            config.resolved_state_path()?,
        )?)),
        StoreBackend::Service => anyhow::bail!(
            "local bridge-store opening requires a file or sqlite backend, not service"
        ),
    }
}

async fn open_service_backed_shared_store(
    service_config: ServiceBackedBridgeStoreConfig,
) -> anyhow::Result<SharedBridgeStore> {
    let backend = ServiceBackedBridgeStore::new(
        service_config.clone(),
        Arc::new(HttpServiceBackedBridgeStoreAdapter::default()),
    );
    let backend_scope =
        deployment_scope_label(ns_storage::BridgeStoreDeploymentScope::SharedDurable);
    match backend.check_health().await {
        Ok(()) => record_bridge_store_service_health(
            "service",
            backend_scope,
            &service_config.endpoint,
            true,
        ),
        Err(error) => {
            record_bridge_store_service_health(
                "service",
                backend_scope,
                &service_config.endpoint,
                false,
            );
            return Err(error).context("service-backed bridge store health check failed");
        }
    }
    Ok(SharedBridgeStore::new(backend))
}

fn require_non_service_store_backend(
    config: &BridgeStoreConfig,
    context: &str,
) -> anyhow::Result<()> {
    if config.backend == StoreBackend::Service {
        anyhow::bail!(
            "{context} requires a local shared-durable backend, not --store-backend service"
        );
    }
    Ok(())
}

fn require_shared_durable_store(store: &SharedBridgeStore) -> anyhow::Result<()> {
    if store.deployment_scope() != ns_storage::BridgeStoreDeploymentScope::SharedDurable {
        anyhow::bail!(
            "bridge serve mode requires a shared durable store backend; got {} ({:?})",
            store.backend_name(),
            store.deployment_scope()
        );
    }
    Ok(())
}

fn build_demo_token_signer() -> anyhow::Result<SessionTokenSigner> {
    let token_signing_key = SigningKey::from_bytes(&[12_u8; 32]);
    let token_pem = token_signing_key
        .to_pkcs8_pem(Default::default())
        .context("failed to encode demo Ed25519 key")?;
    Ok(SessionTokenSigner::from_ed_pem(
        "bridge.example",
        "verta-gateway",
        "bridge-token-2026-01",
        token_pem.as_bytes(),
    )?)
}

fn build_demo_domain(
    store: SharedBridgeStore,
) -> anyhow::Result<BridgeDomain<ns_remnawave_adapter::FakeRemnawaveAdapter, SharedBridgeStore>> {
    Ok(BridgeDomain::new(
        ns_remnawave_adapter::FakeRemnawaveAdapter::with_account(
            BootstrapSubject::ShortUuid("sub-1".to_owned()),
            sample_snapshot(),
        ),
        store,
        demo_manifest_signer()?,
        build_demo_token_signer()?,
        Duration::seconds(300),
    ))
}

fn build_runtime_dependencies(
    config: &RemnawaveAdapterConfig,
    webhook_signature: String,
) -> anyhow::Result<BridgeRuntimeDependencies> {
    let adapter = match config.backend {
        AdapterBackend::Fake => {
            RuntimeRemnawaveAdapter::new(ns_remnawave_adapter::FakeRemnawaveAdapter::with_account(
                BootstrapSubject::ShortUuid("sub-1".to_owned()),
                sample_snapshot(),
            ))
        }
        AdapterBackend::Http => RuntimeRemnawaveAdapter::new(config.build_http()?),
    };

    Ok(BridgeRuntimeDependencies {
        adapter,
        manifest_template: sample_manifest_template(),
        manifest_signer: demo_manifest_signer()?,
        token_signer: build_demo_token_signer()?,
        webhook_authenticator: RuntimeWebhookAuthenticator::new(StaticWebhookAuthenticator {
            expected_signature: webhook_signature,
        }),
        webhook_verification: WebhookVerificationConfig::default(),
        session_token_ttl: Duration::seconds(300),
    })
}

#[cfg(test)]
fn build_fake_runtime_dependencies(
    webhook_signature: String,
) -> anyhow::Result<BridgeRuntimeDependencies> {
    build_runtime_dependencies(
        &RemnawaveAdapterConfig {
            backend: AdapterBackend::Fake,
            base_url: None,
            api_token: None,
            request_timeout_ms: 3_000,
        },
        webhook_signature,
    )
}

fn build_bridge_runtime(
    store: SharedBridgeStore,
    config: BridgeServiceRuntimeConfig,
    dependencies: BridgeRuntimeDependencies,
) -> anyhow::Result<BridgeRuntime> {
    require_shared_durable_store(&store)?;
    let store_backend = store.backend_name();
    let token_jwks = serde_json::to_value(dependencies.token_signer.jwks())
        .context("failed to serialize bridge JWKS")?;
    let domain = Arc::new(BridgeDomain::new(
        dependencies.adapter,
        store,
        dependencies.manifest_signer,
        dependencies.token_signer,
        dependencies.session_token_ttl,
    ));
    let router = build_bridge_router(BridgeHttpServiceState::new(
        domain,
        dependencies.manifest_template,
        Arc::new(dependencies.webhook_authenticator),
        dependencies.webhook_verification,
        token_jwks,
        config.budgets,
    ));
    Ok(BridgeRuntime {
        listen: config.listen,
        router,
        store_backend,
    })
}

fn build_store_service_runtime(
    store: SharedBridgeStore,
    config: BridgeStoreServiceRuntimeConfig,
    auth_token: String,
) -> anyhow::Result<BridgeStoreRuntime> {
    require_shared_durable_store(&store)?;
    if store.backend_name() == "service" {
        anyhow::bail!(
            "bridge store service runtime cannot wrap a service-backed store; supply a local shared-durable backend instead"
        );
    }
    let store_backend = store.backend_name();
    let router = build_service_backed_bridge_store_router(store, Some(auth_token));
    Ok(BridgeStoreRuntime {
        listen: config.listen,
        router,
        store_backend,
    })
}

async fn spawn_managed_http_service(
    listen: SocketAddr,
    router: axum::Router,
    backend: &'static str,
    bind_context: &'static str,
    run_context: &'static str,
) -> anyhow::Result<ManagedServiceRuntime> {
    let listener = tokio::net::TcpListener::bind(listen)
        .await
        .context(bind_context)?;
    let addr = listener
        .local_addr()
        .context("failed to read managed service listener address")?;
    let endpoint = format!("http://{addr}");
    let (shutdown_tx, shutdown_rx) = oneshot::channel();
    let task = tokio::spawn(async move {
        serve(listener, router)
            .with_graceful_shutdown(async move {
                let _ = shutdown_rx.await;
            })
            .await
            .context(run_context)
    });

    Ok(ManagedServiceRuntime {
        endpoint,
        backend,
        shutdown: Some(shutdown_tx),
        task,
    })
}

async fn start_bridge_topology(
    store_config: &BridgeStoreConfig,
    config: BridgeTopologyRuntimeConfig,
    dependencies: BridgeRuntimeDependencies,
    remote_store_auth_token_override: Option<String>,
) -> anyhow::Result<BridgeTopologyRuntime> {
    require_non_service_store_backend(store_config, "bridge deployment topology")?;
    let local_store = open_local_shared_store(store_config)?;
    let store_auth_token = store_config.required_service_store_auth_token()?;
    let store_runtime = build_store_service_runtime(
        local_store,
        BridgeStoreServiceRuntimeConfig {
            listen: config.store_listen,
        },
        store_auth_token.clone(),
    )?;
    let mut store = spawn_managed_http_service(
        store_runtime.listen,
        store_runtime.router,
        store_runtime.store_backend,
        "failed to bind bridge topology store listener",
        "bridge topology store service exited unexpectedly",
    )
    .await?;
    tracing::info!(
        endpoint = %store.endpoint,
        store_backend = store.backend,
        "verta bridge topology store service listening"
    );

    let remote_store_auth_token = remote_store_auth_token_override.unwrap_or(store_auth_token);
    let remote_store = match open_service_backed_shared_store(
        store_config.service_config_for_endpoint_with_auth_token(
            store.endpoint.clone(),
            remote_store_auth_token,
        )?,
    )
    .await
    {
        Ok(store_backend) => store_backend,
        Err(error) => {
            store.request_shutdown();
            let _ = store.join().await;
            return Err(error);
        }
    };

    let bridge_runtime = build_bridge_runtime(
        remote_store,
        BridgeServiceRuntimeConfig {
            listen: config.public_listen,
            budgets: config.budgets,
        },
        dependencies,
    )?;
    let public = match spawn_managed_http_service(
        bridge_runtime.listen,
        bridge_runtime.router,
        bridge_runtime.store_backend,
        "failed to bind bridge topology public listener",
        "bridge topology public service exited unexpectedly",
    )
    .await
    {
        Ok(runtime) => runtime,
        Err(error) => {
            store.request_shutdown();
            let _ = store.join().await;
            return Err(error);
        }
    };
    tracing::info!(
        endpoint = %public.endpoint,
        store_backend = public.backend,
        store_endpoint = %store.endpoint,
        "verta bridge topology public service listening"
    );

    Ok(BridgeTopologyRuntime { public, store })
}

async fn serve_bridge_topology(
    store_config: &BridgeStoreConfig,
    config: BridgeTopologyRuntimeConfig,
    dependencies: BridgeRuntimeDependencies,
) -> anyhow::Result<()> {
    start_bridge_topology(store_config, config, dependencies, None)
        .await?
        .wait()
        .await
}

async fn compile_demo_manifest(
    store: SharedBridgeStore,
    generated_at_unix: Option<i64>,
) -> anyhow::Result<()> {
    let domain = build_demo_domain(store.clone())?;
    let generated_at = generated_at_unix
        .map(OffsetDateTime::from_unix_timestamp)
        .transpose()
        .context("generated_at_unix was not a valid unix timestamp")?
        .unwrap_or_else(OffsetDateTime::now_utc);

    let manifest = domain.compile_manifest(
        sample_manifest_template().compile_input(
            domain
                .resolve_bootstrap(&BootstrapSubject::ShortUuid("sub-1".to_owned()))
                .await?,
            None,
        ),
        generated_at,
    )?;

    println!("{}", serde_json::to_string_pretty(&manifest)?);
    Ok(())
}

async fn serve_bridge_runtime(runtime: BridgeRuntime) -> anyhow::Result<()> {
    let listener = tokio::net::TcpListener::bind(runtime.listen)
        .await
        .context("failed to bind bridge HTTP listener")?;
    tracing::info!(
        listen = %runtime.listen,
        store_backend = runtime.store_backend,
        "verta bridge HTTP service listening"
    );
    serve(listener, runtime.router)
        .await
        .context("bridge HTTP server exited unexpectedly")?;
    Ok(())
}

async fn serve_store_runtime(runtime: BridgeStoreRuntime) -> anyhow::Result<()> {
    let listener = tokio::net::TcpListener::bind(runtime.listen)
        .await
        .context("failed to bind bridge store listener")?;
    tracing::info!(
        listen = %runtime.listen,
        store_backend = runtime.store_backend,
        "verta bridge store service listening"
    );
    serve(listener, runtime.router)
        .await
        .context("bridge store service exited unexpectedly")?;
    Ok(())
}

fn demo_manifest_signer() -> anyhow::Result<ManifestSigner> {
    Ok(ManifestSigner::new(
        "bridge-manifest-2026-01",
        SigningKey::from_bytes(&[13_u8; 32]),
    ))
}

fn sample_manifest_template() -> BridgeManifestTemplate {
    BridgeManifestTemplate {
        context: BridgeManifestContext {
            device_policy: Some(DevicePolicy {
                max_devices: 2,
                require_device_binding: true,
            }),
            client_constraints: ClientConstraints {
                min_client_version: "0.1.0".to_owned(),
                recommended_client_version: "0.1.0".to_owned(),
                allowed_core_versions: vec![1],
            },
            token_service: TokenService {
                url: Url::parse("https://bridge.example/v0/token/exchange")
                    .expect("fixture token-service url should parse"),
                issuer: "bridge.example".to_owned(),
                jwks_url: Url::parse("https://bridge.example/.well-known/jwks.json")
                    .expect("fixture jwks url should parse"),
                session_token_ttl_seconds: 300,
            },
            refresh: Some(RefreshPolicy {
                mode: RefreshMode::OpaqueSecret,
                credential: "bootstrap-only-redacted".to_owned(),
                rotation_hint_seconds: Some(86_400),
            }),
            routing: RoutingPolicy {
                selection_mode: RoutingSelectionMode::LatencyWeighted,
                failover_mode: RoutingFailoverMode::SameRegionThenGlobal,
            },
            retry_policy: RetryPolicy {
                connect_attempts: 3,
                initial_backoff_ms: 500,
                max_backoff_ms: 10_000,
            },
            telemetry: TelemetryPolicy {
                allow_client_reports: true,
                sample_rate: 0.05,
            },
        },
        carrier_profiles: vec![BridgeCarrierProfile {
            id: "carrier-primary".to_owned(),
            carrier_kind: ManifestCarrierKind::H3,
            origin_host: "origin.edge.example.net".to_owned(),
            origin_port: 8443,
            sni: Some("origin.edge.example.net".to_owned()),
            alpn: vec!["h3".to_owned()],
            control_template: HttpTemplate {
                method: HttpTemplateMethod::Connect,
                path: "/ns/control".to_owned(),
            },
            relay_template: HttpTemplate {
                method: HttpTemplateMethod::Connect,
                path: "/ns/relay".to_owned(),
            },
            headers: BTreeMap::from([("x-verta-profile".to_owned(), "carrier-primary".to_owned())]),
            datagram_enabled: false,
            heartbeat_interval_ms: 20_000,
            idle_timeout_ms: 90_000,
            zero_rtt_policy: Some(ZeroRttPolicy::Disabled),
            connect_backoff: ConnectBackoff {
                initial_ms: 500,
                max_ms: 10_000,
                jitter: 0.2,
            },
        }],
        endpoints: vec![BridgeGatewayEndpoint {
            id: "edge-1".to_owned(),
            host: "edge.example.net".to_owned(),
            port: 443,
            region: "eu-central".to_owned(),
            routing_group: Some("primary".to_owned()),
            carrier_profile_ids: vec!["carrier-primary".to_owned()],
            priority: 10,
            weight: 100,
            tags: vec!["stable".to_owned(), "demo".to_owned()],
        }],
        manifest_ttl: Duration::hours(6),
        bootstrap_grant_ttl: Duration::minutes(5),
    }
}

fn sample_snapshot() -> AccountSnapshot {
    AccountSnapshot {
        account_id: "acct-1".to_owned(),
        bootstrap_subjects: vec![BootstrapSubject::ShortUuid("sub-1".to_owned())],
        lifecycle: AccountLifecycle::Active,
        verta_access: VertaAccess {
            verta_enabled: true,
            policy_epoch: 7,
            device_limit: Some(2),
            allowed_core_versions: vec![1],
            allowed_carrier_profiles: vec!["carrier-primary".to_owned()],
            allowed_capabilities: vec![1, 2],
            rollout_cohort: Some("alpha".to_owned()),
            preferred_regions: vec!["eu-central".to_owned()],
        },
        metadata: None,
        observed_at_unix: 1_700_000_000,
        source_version: Some("2.7.4".to_owned()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::{Body, to_bytes};
    use axum::extract::{Path as AxumPath, State};
    use axum::http::HeaderMap;
    use axum::http::StatusCode;
    use axum::http::header::{AUTHORIZATION, ETAG, IF_NONE_MATCH};
    use axum::routing::{get, post};
    use axum::{Json, Router};
    use serde_json::json;
    use std::collections::HashMap;
    use std::fs;
    use std::io::ErrorKind;
    use std::path::{Path, PathBuf};
    use std::sync::atomic::{AtomicU64, Ordering};
    use std::sync::{Arc, Mutex};
    use tokio::net::TcpListener;
    use tower::ServiceExt;

    struct TestRemnawaveState {
        account: Mutex<Option<AccountSnapshot>>,
        metadata: Mutex<HashMap<String, serde_json::Value>>,
        expected_token: String,
    }

    fn unique_test_path_nonce() -> u64 {
        static NEXT_NONCE: AtomicU64 = AtomicU64::new(0);
        NEXT_NONCE.fetch_add(1, Ordering::Relaxed)
    }

    fn temporary_sqlite_store_path() -> PathBuf {
        let mut path = std::env::temp_dir();
        let nonce = unique_test_path_nonce();
        path.push(format!(
            "verta-bridge-app-{}-{nonce}.sqlite3",
            std::process::id()
        ));
        path
    }

    fn cleanup_sqlite_store_path(path: &Path) {
        let candidates = [
            path.to_path_buf(),
            PathBuf::from(format!("{}-wal", path.display())),
            PathBuf::from(format!("{}-shm", path.display())),
        ];

        for _ in 0..10 {
            let mut busy = false;
            let mut remaining = false;

            for candidate in &candidates {
                if !candidate.exists() {
                    continue;
                }
                remaining = true;
                match fs::remove_file(candidate) {
                    Ok(()) => {}
                    Err(error)
                        if error.kind() == ErrorKind::NotFound
                            || error.raw_os_error() == Some(2) => {}
                    Err(error)
                        if error.kind() == ErrorKind::PermissionDenied
                            || error.raw_os_error() == Some(32) =>
                    {
                        busy = true;
                        break;
                    }
                    Err(error) => panic!(
                        "sqlite test store artifact should be removable ({}): {error}",
                        candidate.display()
                    ),
                }
            }

            if !busy && (!remaining || candidates.iter().all(|candidate| !candidate.exists())) {
                return;
            }

            std::thread::sleep(std::time::Duration::from_millis(25));
        }

        let remaining: Vec<String> = candidates
            .iter()
            .filter(|candidate| candidate.exists())
            .map(|candidate| candidate.display().to_string())
            .collect();
        panic!(
            "sqlite test store artifacts should be removable after retries: {}",
            remaining.join(", ")
        );
    }

    async fn spawn_router(router: Router) -> (String, tokio::task::JoinHandle<()>) {
        let listener = TcpListener::bind("127.0.0.1:0")
            .await
            .expect("test listener should bind");
        let addr = listener
            .local_addr()
            .expect("test listener should expose a local address");
        let handle = tokio::spawn(async move {
            axum::serve(listener, router)
                .await
                .expect("test service should serve requests");
        });
        tokio::time::sleep(std::time::Duration::from_millis(10)).await;
        (format!("http://{addr}"), handle)
    }

    async fn request_store_health_until_ready(
        store_endpoint: &str,
        auth_token: &str,
    ) -> reqwest::Response {
        let client = reqwest::Client::new();
        let url = format!("{store_endpoint}/internal/store/v1/health");
        let mut last_outcome = None;

        for _ in 0..10 {
            match client.get(&url).bearer_auth(auth_token).send().await {
                Ok(response) if response.status() == reqwest::StatusCode::OK => return response,
                Ok(response) => {
                    last_outcome = Some(format!("unexpected status {}", response.status()));
                }
                Err(error) => {
                    last_outcome = Some(error.to_string());
                }
            }
            tokio::time::sleep(std::time::Duration::from_millis(25)).await;
        }

        panic!(
            "store health request should succeed: {}",
            last_outcome.unwrap_or_else(|| "unknown readiness failure".to_owned())
        );
    }

    fn authorized(headers: &HeaderMap, expected_token: &str) -> bool {
        headers
            .get(AUTHORIZATION)
            .and_then(|value| value.to_str().ok())
            .and_then(|value| value.strip_prefix("Bearer "))
            == Some(expected_token)
    }

    async fn resolve_user(
        State(state): State<Arc<TestRemnawaveState>>,
        headers: HeaderMap,
    ) -> Result<Json<AccountSnapshot>, StatusCode> {
        if !authorized(&headers, &state.expected_token) {
            return Err(StatusCode::UNAUTHORIZED);
        }
        let snapshot = state
            .account
            .lock()
            .expect("test remnawave state poisoned")
            .clone()
            .ok_or(StatusCode::NOT_FOUND)?;
        Ok(Json(snapshot))
    }

    async fn get_user(
        State(state): State<Arc<TestRemnawaveState>>,
        headers: HeaderMap,
        AxumPath(account_id): AxumPath<String>,
    ) -> Result<Json<AccountSnapshot>, StatusCode> {
        if !authorized(&headers, &state.expected_token) {
            return Err(StatusCode::UNAUTHORIZED);
        }
        let snapshot = state
            .account
            .lock()
            .expect("test remnawave state poisoned")
            .clone()
            .ok_or(StatusCode::NOT_FOUND)?;
        if snapshot.account_id != account_id {
            return Err(StatusCode::NOT_FOUND);
        }
        Ok(Json(snapshot))
    }

    async fn get_metadata(
        State(state): State<Arc<TestRemnawaveState>>,
        headers: HeaderMap,
        AxumPath(account_id): AxumPath<String>,
    ) -> Result<Json<serde_json::Value>, StatusCode> {
        if !authorized(&headers, &state.expected_token) {
            return Err(StatusCode::UNAUTHORIZED);
        }
        state
            .metadata
            .lock()
            .expect("test remnawave state poisoned")
            .get(&account_id)
            .cloned()
            .map(Json)
            .ok_or(StatusCode::NOT_FOUND)
    }

    async fn put_metadata(
        State(state): State<Arc<TestRemnawaveState>>,
        headers: HeaderMap,
        AxumPath(account_id): AxumPath<String>,
        Json(patch): Json<serde_json::Value>,
    ) -> Result<StatusCode, StatusCode> {
        if !authorized(&headers, &state.expected_token) {
            return Err(StatusCode::UNAUTHORIZED);
        }
        state
            .metadata
            .lock()
            .expect("test remnawave state poisoned")
            .insert(account_id, patch);
        Ok(StatusCode::NO_CONTENT)
    }

    fn build_test_remnawave_router(expected_token: &str) -> Router {
        let state = Arc::new(TestRemnawaveState {
            account: Mutex::new(Some(sample_snapshot())),
            metadata: Mutex::new(HashMap::new()),
            expected_token: expected_token.to_owned(),
        });
        Router::new()
            .route("/api/users/resolve", post(resolve_user))
            .route("/api/users/{account_id}", get(get_user))
            .route(
                "/api/users/{account_id}/metadata",
                get(get_metadata).put(put_metadata),
            )
            .with_state(state)
    }

    async fn spawn_store_service(
        path: &Path,
        auth_token: &str,
    ) -> anyhow::Result<(String, tokio::task::JoinHandle<()>)> {
        let store = SharedBridgeStore::new(SqliteBridgeStore::open(path)?);
        let runtime = build_store_service_runtime(
            store,
            BridgeStoreServiceRuntimeConfig {
                listen: "127.0.0.1:0"
                    .parse()
                    .expect("test store listen address should parse"),
            },
            auth_token.to_owned(),
        )?;
        Ok(spawn_router(runtime.router).await)
    }

    async fn open_remote_store(
        endpoint: String,
        auth_token: &str,
    ) -> anyhow::Result<SharedBridgeStore> {
        open_shared_store(&BridgeStoreConfig {
            backend: StoreBackend::Service,
            state_path: None,
            service_store_endpoint: Some(endpoint),
            service_store_timeout_ms: 500,
            service_store_auth_token: Some(auth_token.to_owned()),
            service_store_fallback_endpoints: Vec::new(),
        })
        .await
    }

    fn topology_store_config(path: &Path, auth_token: &str) -> BridgeStoreConfig {
        BridgeStoreConfig {
            backend: StoreBackend::Sqlite,
            state_path: Some(path.to_path_buf()),
            service_store_endpoint: None,
            service_store_timeout_ms: 500,
            service_store_auth_token: Some(auth_token.to_owned()),
            service_store_fallback_endpoints: Vec::new(),
        }
    }

    fn topology_runtime_config() -> BridgeTopologyRuntimeConfig {
        BridgeTopologyRuntimeConfig {
            public_listen: "127.0.0.1:0"
                .parse()
                .expect("test bridge topology public address should parse"),
            store_listen: "127.0.0.1:0"
                .parse()
                .expect("test bridge topology store address should parse"),
            budgets: BridgeHttpBudgets::default(),
        }
    }

    fn build_test_runtime(path: &Path) -> anyhow::Result<BridgeRuntime> {
        let store = SharedBridgeStore::new(SqliteBridgeStore::open(path)?);
        build_bridge_runtime(
            store,
            BridgeServiceRuntimeConfig {
                listen: "127.0.0.1:0"
                    .parse()
                    .expect("test bridge listen address should parse"),
                budgets: BridgeHttpBudgets::default(),
            },
            build_fake_runtime_dependencies("sig-ok".to_owned())?,
        )
    }

    async fn build_remote_runtime_with_fake_adapter(
        endpoint: String,
        auth_token: &str,
    ) -> anyhow::Result<BridgeRuntime> {
        build_bridge_runtime(
            open_remote_store(endpoint, auth_token).await?,
            BridgeServiceRuntimeConfig {
                listen: "127.0.0.1:0"
                    .parse()
                    .expect("test bridge listen address should parse"),
                budgets: BridgeHttpBudgets::default(),
            },
            build_fake_runtime_dependencies("sig-ok".to_owned())?,
        )
    }

    async fn build_remote_runtime_with_http_adapter(
        store_endpoint: String,
        store_auth_token: &str,
        remnawave_base_url: String,
        remnawave_api_token: &str,
    ) -> anyhow::Result<BridgeRuntime> {
        build_bridge_runtime(
            open_remote_store(store_endpoint, store_auth_token).await?,
            BridgeServiceRuntimeConfig {
                listen: "127.0.0.1:0"
                    .parse()
                    .expect("test bridge listen address should parse"),
                budgets: BridgeHttpBudgets::default(),
            },
            build_runtime_dependencies(
                &RemnawaveAdapterConfig {
                    backend: AdapterBackend::Http,
                    base_url: Some(remnawave_base_url),
                    api_token: Some(remnawave_api_token.to_owned()),
                    request_timeout_ms: 500,
                },
                "sig-ok".to_owned(),
            )?,
        )
    }

    async fn exercise_public_bridge_flow_over_http(base_url: &str) {
        let client = reqwest::Client::new();
        let manifest_response = client
            .get(format!("{base_url}/v0/manifest?subscription_token=sub-1"))
            .send()
            .await
            .expect("manifest request should succeed");
        assert_eq!(manifest_response.status(), reqwest::StatusCode::OK);
        let manifest: ns_manifest::ManifestDocument = manifest_response
            .json()
            .await
            .expect("manifest response should parse");
        let bootstrap_credential = manifest
            .refresh
            .as_ref()
            .map(|refresh| refresh.credential.clone())
            .expect("bootstrap manifest should carry a bootstrap credential");

        let register_response = client
            .post(format!("{base_url}/v0/device/register"))
            .bearer_auth(&bootstrap_credential)
            .json(&json!({
                "manifest_id": manifest.manifest_id,
                "device_id": "device-1",
                "device_name": "Workstation",
                "platform": "windows",
                "client_version": "0.1.0",
                "install_channel": "stable",
                "requested_capabilities": [1, 2],
            }))
            .send()
            .await
            .expect("device register request should succeed");
        assert_eq!(register_response.status(), reqwest::StatusCode::OK);
        let register: ns_bridge_api::DeviceRegisterResponse = register_response
            .json()
            .await
            .expect("device register response should parse");
        let refresh_credential = register
            .refresh_credential
            .expect("device register should issue a refresh credential");

        let exchange_response = client
            .post(format!("{base_url}/v0/token/exchange"))
            .json(&ns_bridge_api::TokenExchangeRequest {
                manifest_id: manifest.manifest_id.clone(),
                device_id: "device-1".to_owned(),
                client_version: "0.1.0".to_owned(),
                core_version: 1,
                carrier_profile_id: "carrier-primary".to_owned(),
                requested_capabilities: vec![1, 2],
                refresh_credential: refresh_credential.clone(),
            })
            .send()
            .await
            .expect("token exchange request should succeed");
        assert_eq!(exchange_response.status(), reqwest::StatusCode::OK);
        let exchange: ns_bridge_api::TokenExchangeResponse = exchange_response
            .json()
            .await
            .expect("token exchange response should parse");
        assert!(!exchange.session_token.is_empty());

        let refresh_manifest = client
            .get(format!("{base_url}/v0/manifest"))
            .bearer_auth(&refresh_credential)
            .send()
            .await
            .expect("refresh manifest request should succeed");
        assert_eq!(refresh_manifest.status(), reqwest::StatusCode::OK);
    }

    #[tokio::test]
    async fn bridge_runtime_serves_manifest_register_token_exchange_and_refresh_over_shared_durable_store()
     {
        let path = temporary_sqlite_store_path();
        let runtime = build_test_runtime(path.as_path()).expect("bridge runtime should build");
        let router = runtime.router.clone();

        let manifest_response = router
            .clone()
            .oneshot(
                axum::http::Request::builder()
                    .uri("/v0/manifest?subscription_token=sub-1")
                    .body(Body::empty())
                    .expect("manifest request should build"),
            )
            .await
            .expect("manifest request should succeed");
        assert_eq!(manifest_response.status(), StatusCode::OK);
        let manifest_body = to_bytes(manifest_response.into_body(), usize::MAX)
            .await
            .expect("manifest body should read");
        let manifest: ns_manifest::ManifestDocument =
            serde_json::from_slice(manifest_body.as_ref()).expect("manifest should parse");
        let bootstrap_credential = manifest
            .refresh
            .as_ref()
            .map(|refresh| refresh.credential.clone())
            .expect("bootstrap manifest should carry a bootstrap credential");

        let register_response = router
            .clone()
            .oneshot(
                axum::http::Request::builder()
                    .method("POST")
                    .uri("/v0/device/register")
                    .header(AUTHORIZATION, format!("Bearer {bootstrap_credential}"))
                    .header("content-type", "application/json")
                    .body(Body::from(
                        serde_json::to_vec(&json!({
                            "manifest_id": manifest.manifest_id,
                            "device_id": "device-1",
                            "device_name": "Workstation",
                            "platform": "windows",
                            "client_version": "0.1.0",
                            "install_channel": "stable",
                            "requested_capabilities": [1, 2],
                        }))
                        .expect("device register request should serialize"),
                    ))
                    .expect("device register request should build"),
            )
            .await
            .expect("device register request should succeed");
        assert_eq!(register_response.status(), StatusCode::OK);
        let register_body = to_bytes(register_response.into_body(), usize::MAX)
            .await
            .expect("device register body should read");
        let register: ns_bridge_api::DeviceRegisterResponse =
            serde_json::from_slice(register_body.as_ref())
                .expect("device register response should parse");
        let refresh_credential = register
            .refresh_credential
            .expect("device register should issue a refresh credential");

        let exchange_response = router
            .clone()
            .oneshot(
                axum::http::Request::builder()
                    .method("POST")
                    .uri("/v0/token/exchange")
                    .header("content-type", "application/json")
                    .body(Body::from(
                        serde_json::to_vec(&ns_bridge_api::TokenExchangeRequest {
                            manifest_id: manifest.manifest_id.clone(),
                            device_id: "device-1".to_owned(),
                            client_version: "0.1.0".to_owned(),
                            core_version: 1,
                            carrier_profile_id: "carrier-primary".to_owned(),
                            requested_capabilities: vec![1, 2],
                            refresh_credential: refresh_credential.clone(),
                        })
                        .expect("token exchange request should serialize"),
                    ))
                    .expect("token exchange request should build"),
            )
            .await
            .expect("token exchange request should succeed");
        assert_eq!(exchange_response.status(), StatusCode::OK);
        let exchange_body = to_bytes(exchange_response.into_body(), usize::MAX)
            .await
            .expect("token exchange body should read");
        let exchange: ns_bridge_api::TokenExchangeResponse =
            serde_json::from_slice(exchange_body.as_ref())
                .expect("token exchange response should parse");
        assert!(!exchange.session_token.is_empty());

        let refresh_manifest = router
            .clone()
            .oneshot(
                axum::http::Request::builder()
                    .uri("/v0/manifest")
                    .header(AUTHORIZATION, format!("Bearer {refresh_credential}"))
                    .body(Body::empty())
                    .expect("refresh manifest request should build"),
            )
            .await
            .expect("refresh manifest request should succeed");
        assert_eq!(refresh_manifest.status(), StatusCode::OK);
        let refresh_etag = refresh_manifest
            .headers()
            .get(ETAG)
            .and_then(|value| value.to_str().ok())
            .map(str::to_owned)
            .expect("refresh manifest should expose an etag");

        let conditional = router
            .clone()
            .oneshot(
                axum::http::Request::builder()
                    .uri("/v0/manifest")
                    .header(AUTHORIZATION, format!("Bearer {refresh_credential}"))
                    .header(IF_NONE_MATCH, refresh_etag)
                    .body(Body::empty())
                    .expect("conditional refresh request should build"),
            )
            .await
            .expect("conditional refresh request should succeed");
        assert!(
            matches!(
                conditional.status(),
                StatusCode::OK | StatusCode::NOT_MODIFIED
            ),
            "conditional refresh should either reuse the compiled manifest or produce a fresh one"
        );

        drop(router);
        drop(runtime);
        cleanup_sqlite_store_path(path.as_path());
    }

    #[tokio::test]
    async fn bridge_runtime_deduplicates_webhooks_over_shared_durable_store() {
        let path = temporary_sqlite_store_path();
        let runtime = build_test_runtime(path.as_path()).expect("bridge runtime should build");
        let router = runtime.router.clone();
        let now = OffsetDateTime::now_utc().unix_timestamp();
        let payload = json!({
            "event_id": "evt-1",
            "event_type": "subscription.updated",
            "account_id": "acct-1",
            "occurred_at_unix": now,
            "payload": { "plan": "pro" }
        });

        let request = || {
            axum::http::Request::builder()
                .method("POST")
                .uri("/internal/remnawave/webhook")
                .header("x-remnawave-signature", "sig-ok")
                .header("x-remnawave-timestamp", now.to_string())
                .header("content-type", "application/json")
                .body(Body::from(
                    serde_json::to_vec(&payload).expect("webhook request should serialize"),
                ))
                .expect("webhook request should build")
        };

        let first = router
            .clone()
            .oneshot(request())
            .await
            .expect("first webhook delivery should succeed");
        assert_eq!(first.status(), StatusCode::OK);

        let duplicate = router
            .clone()
            .oneshot(request())
            .await
            .expect("duplicate webhook delivery should return a response");
        assert_eq!(duplicate.status(), StatusCode::CONFLICT);

        drop(router);
        drop(runtime);
        cleanup_sqlite_store_path(path.as_path());
    }

    #[tokio::test]
    async fn bridge_runtime_serves_public_flow_over_remote_store_service() {
        let path = temporary_sqlite_store_path();
        let (store_endpoint, store_handle) = spawn_store_service(path.as_path(), "store-secret")
            .await
            .expect("store service should start");
        let runtime =
            build_remote_runtime_with_fake_adapter(store_endpoint.clone(), "store-secret")
                .await
                .expect("bridge runtime should build against the remote store service");
        let health = request_store_health_until_ready(&store_endpoint, "store-secret").await;
        assert_eq!(health.status(), reqwest::StatusCode::OK);
        let (public_endpoint, public_handle) = spawn_router(runtime.router.clone()).await;

        exercise_public_bridge_flow_over_http(&public_endpoint).await;

        public_handle.abort();
        let _ = public_handle.await;
        drop(runtime);
        store_handle.abort();
        let _ = store_handle.await;
        cleanup_sqlite_store_path(path.as_path());
    }

    #[tokio::test]
    async fn bridge_runtime_supports_http_remnawave_adapter_over_remote_store_service() {
        let path = temporary_sqlite_store_path();
        let (store_endpoint, store_handle) = spawn_store_service(path.as_path(), "store-secret")
            .await
            .expect("store service should start");
        let (remnawave_base_url, remnawave_handle) =
            spawn_router(build_test_remnawave_router("rw-token")).await;
        let runtime = build_remote_runtime_with_http_adapter(
            store_endpoint,
            "store-secret",
            remnawave_base_url,
            "rw-token",
        )
        .await
        .expect("bridge runtime should build against the HTTP remnawave adapter");
        let (public_endpoint, public_handle) = spawn_router(runtime.router.clone()).await;

        exercise_public_bridge_flow_over_http(&public_endpoint).await;

        public_handle.abort();
        let _ = public_handle.await;
        drop(runtime);
        remnawave_handle.abort();
        let _ = remnawave_handle.await;
        store_handle.abort();
        let _ = store_handle.await;
        cleanup_sqlite_store_path(path.as_path());
    }

    #[tokio::test]
    async fn bridge_topology_runtime_starts_passes_health_and_shuts_down_cleanly() {
        let path = temporary_sqlite_store_path();
        let topology = start_bridge_topology(
            &topology_store_config(path.as_path(), "store-secret"),
            topology_runtime_config(),
            build_fake_runtime_dependencies("sig-ok".to_owned())
                .expect("test dependencies should build"),
            None,
        )
        .await
        .expect("bridge topology should start");
        let store_endpoint = topology.store.endpoint.clone();
        let public_endpoint = topology.public.endpoint.clone();

        let health = request_store_health_until_ready(&store_endpoint, "store-secret").await;
        assert_eq!(health.status(), reqwest::StatusCode::OK);

        exercise_public_bridge_flow_over_http(&public_endpoint).await;
        topology
            .shutdown()
            .await
            .expect("bridge topology should shut down cleanly");

        let shutdown_error = reqwest::Client::new()
            .get(format!(
                "{public_endpoint}/v0/manifest?subscription_token=sub-1"
            ))
            .send()
            .await
            .expect_err("public bridge endpoint should stop accepting requests after shutdown");
        assert!(
            shutdown_error.is_connect()
                || shutdown_error.is_request()
                || shutdown_error.is_timeout(),
            "expected a transport-level request error after shutdown, got: {shutdown_error}"
        );

        cleanup_sqlite_store_path(path.as_path());
    }

    #[tokio::test]
    async fn bridge_topology_fails_closed_on_remote_store_auth_mismatch() {
        let path = temporary_sqlite_store_path();
        let error = match start_bridge_topology(
            &topology_store_config(path.as_path(), "store-secret"),
            topology_runtime_config(),
            build_fake_runtime_dependencies("sig-ok".to_owned())
                .expect("test dependencies should build"),
            Some("wrong-secret".to_owned()),
        )
        .await
        {
            Ok(_) => panic!("bridge topology should fail closed on remote store auth mismatch"),
            Err(error) => error,
        };

        let error_text = format!("{error:#}");
        assert!(
            error_text.contains("health check failed") || error_text.contains("HTTP 401"),
            "unexpected topology auth failure: {error_text}"
        );

        cleanup_sqlite_store_path(path.as_path());
    }

    #[tokio::test]
    async fn bridge_topology_supports_http_remnawave_adapter_against_realistic_upstream() {
        let path = temporary_sqlite_store_path();
        let (remnawave_base_url, remnawave_handle) =
            spawn_router(build_test_remnawave_router("rw-token")).await;
        let topology = start_bridge_topology(
            &topology_store_config(path.as_path(), "store-secret"),
            topology_runtime_config(),
            build_runtime_dependencies(
                &RemnawaveAdapterConfig {
                    backend: AdapterBackend::Http,
                    base_url: Some(remnawave_base_url),
                    api_token: Some("rw-token".to_owned()),
                    request_timeout_ms: 500,
                },
                "sig-ok".to_owned(),
            )
            .expect("HTTP Remnawave runtime dependencies should build"),
            None,
        )
        .await
        .expect("bridge topology should start against the HTTP Remnawave adapter");
        let public_endpoint = topology.public.endpoint.clone();

        exercise_public_bridge_flow_over_http(&public_endpoint).await;

        topology
            .shutdown()
            .await
            .expect("bridge topology should shut down cleanly");
        remnawave_handle.abort();
        let _ = remnawave_handle.await;
        cleanup_sqlite_store_path(path.as_path());
    }

    #[tokio::test]
    async fn bridge_remote_store_mode_requires_an_auth_token() {
        let error = match open_shared_store(&BridgeStoreConfig {
            backend: StoreBackend::Service,
            state_path: None,
            service_store_endpoint: Some("http://127.0.0.1:18081".to_owned()),
            service_store_timeout_ms: 500,
            service_store_auth_token: None,
            service_store_fallback_endpoints: Vec::new(),
        })
        .await
        {
            Ok(_) => panic!("remote store mode should require an auth token"),
            Err(error) => error,
        };

        assert!(
            error.to_string().contains("--service-store-auth-token"),
            "unexpected error: {error}"
        );
    }
}
