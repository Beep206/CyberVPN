import { getTranslations } from 'next-intl/server';
import { Terminal } from 'lucide-react';
import { DocsCodeBlock } from '@/widgets/docs-code-block';

const INSTALL_CODE = `curl -sL https://cybervpn.net/install.sh | bash
sudo systemctl enable cybervpn-core
cybervpn auth --token=YOUR_NEURAL_ID`;

const ROUTING_CODE = `{
  "routing": {
    "domainStrategy": "AsIs",
    "rules": [
      {
        "type": "field",
        "outboundTag": "proxy",
        "domain": ["geosite:geolocation-!cn"]
      },
      {
        "type": "field",
        "outboundTag": "direct",
        "domain": ["geosite:cn", "geosite:private"]
      }
    ]
  }
}`;

const API_CODE = `import { CyberVPN } from '@cybervpn/sdk';

const client = new CyberVPN({
  token: process.env.CYBER_NEURAL_TOKEN,
  endpoint: 'api.cybervpn.net/v1'
});

const session = await client.connect({
  mode: 'stealth',
  region: 'EU-West'
});

console.log('Neural Link Active:', session.ip);`;

export async function DocsContentServer() {
  const t = await getTranslations('Docs');

  return (
    <>
      <div className="border-b border-terminal-border/30 pb-12 pt-4 lg:pb-16 lg:pt-8">
        <p className="mb-4 flex items-center gap-2 font-cyber tracking-[0.2em] text-neon-cyan">
          <Terminal className="h-4 w-4" /> &gt; {t('subtitle')}
        </p>
        <h1 className="text-4xl font-black text-foreground drop-shadow-[0_0_15px_rgba(255,255,255,0.1)] md:text-6xl">
          {t('title')}
        </h1>
        <p className="mt-6 max-w-2xl text-lg font-mono leading-relaxed text-muted-foreground">
          {t('meta_description')}
        </p>
      </div>

      <section
        id="getting_started"
        data-anchor
        className="relative scroll-mt-28 lg:scroll-mt-32"
      >
        <div className="absolute bottom-0 top-0 -left-8 w-px bg-gradient-to-b from-matrix-green/50 to-transparent" />
        <h2 className="mb-6 flex items-center gap-4 text-3xl font-display font-bold text-matrix-green">
          <span className="text-sm font-mono opacity-50">01.</span>
          {t('section_getting_started')}
        </h2>

        <div className="space-y-6 font-mono leading-relaxed text-muted-foreground">
          <h3 className="mb-4 mt-8 text-xl text-foreground">{t('doc_install_title')}</h3>
          <p>{t('doc_install_desc')}</p>

          <DocsCodeBlock language="bash" code={INSTALL_CODE} />

          <p>
            Upon successful initialization, the core daemon will daemonize and
            establish a local proxy endpoint on{' '}
            <code className="rounded bg-neon-cyan/10 px-1 py-0.5 text-neon-cyan">
              127.0.0.1:1080
            </code>
            .
          </p>
        </div>
      </section>

      <section
        id="routing"
        data-anchor
        className="relative scroll-mt-28 lg:scroll-mt-32"
      >
        <div className="absolute bottom-0 top-0 -left-8 w-px bg-gradient-to-b from-neon-pink/50 to-transparent" />
        <h2 className="mb-6 flex items-center gap-4 text-3xl font-display font-bold text-neon-pink">
          <span className="text-sm font-mono opacity-50">02.</span>
          {t('section_routing')}
        </h2>

        <div className="space-y-6 font-mono leading-relaxed text-muted-foreground">
          <h3 className="mb-4 mt-8 text-xl text-foreground">{t('doc_config_title')}</h3>
          <p>{t('doc_config_desc')}</p>

          <DocsCodeBlock language="json" code={ROUTING_CODE} />
        </div>
      </section>

      <section
        id="security"
        data-anchor
        className="relative scroll-mt-28 lg:scroll-mt-32"
      >
        <div className="absolute bottom-0 top-0 -left-8 w-px bg-gradient-to-b from-neon-cyan/50 to-transparent" />
        <h2 className="mb-6 flex items-center gap-4 text-3xl font-display font-bold text-neon-cyan">
          <span className="text-sm font-mono opacity-50">03.</span>
          {t('section_security')}
        </h2>

        <div className="space-y-6 font-mono leading-relaxed text-muted-foreground">
          <h3 className="mb-4 mt-8 text-xl text-foreground">{t('doc_protocols_title')}</h3>
          <p>{t('doc_protocols_desc')}</p>

          <div className="group relative overflow-hidden border border-terminal-border/40 bg-terminal-bg/30 p-4">
            <div className="absolute left-0 top-0 h-px w-full bg-gradient-to-r from-neon-cyan to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
            <h4 className="mb-2 text-neon-cyan">VLESS + XTLS-Reality</h4>
            <p className="text-sm">
              The recommended configuration for maximum DPI evasion. Strips TLS
              overhead while maintaining perfect forward secrecy via x25519 elliptic
              curves.
            </p>
          </div>
        </div>
      </section>

      <section id="api" data-anchor className="relative scroll-mt-28 lg:scroll-mt-32">
        <div className="absolute bottom-0 top-0 -left-8 w-px bg-gradient-to-b from-warning/50 to-transparent" />
        <h2 className="mb-6 flex items-center gap-4 text-3xl font-display font-bold text-warning">
          <span className="text-sm font-mono opacity-50">04.</span>
          {t('section_api')}
        </h2>

        <div className="space-y-6 font-mono leading-relaxed text-muted-foreground">
          <h3 className="mb-4 mt-8 text-xl text-foreground">Neural API Interface</h3>
          <p>
            Integrate directly with the VPN core using our high-performance gRPC
            or REST endpoints. Authentication is handled via bearer tokens
            generated in the dashboard.
          </p>

          <DocsCodeBlock language="typescript" code={API_CODE} />
        </div>
      </section>
    </>
  );
}
