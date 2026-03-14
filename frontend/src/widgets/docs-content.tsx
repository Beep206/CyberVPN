'use client';

import { useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { motion, AnimatePresence } from 'motion/react';
import { Copy, Check, Terminal } from 'lucide-react';
import { ScrambleText } from '@/shared/ui/scramble-text';

export function DocsContent({ onSectionChange }: { onSectionChange: (id: string) => void }) {
    const t = useTranslations('Docs');
    
    // Set up intersection observer to detect active section
    useEffect(() => {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    onSectionChange(entry.target.id);
                }
            });
        }, {
            // Trigger when section hits upper third of screen
            rootMargin: '-10% 0px -70% 0px',
            threshold: 0
        });

        const sections = document.querySelectorAll('section[data-anchor]');
        sections.forEach((s) => observer.observe(s));

        return () => observer.disconnect();
    }, [onSectionChange]);

    return (
        <div className="w-full flex-1 max-w-3xl space-y-32 pb-[80vh]">
            
            {/* Header Area */}
            <div className="pt-8 pb-16 border-b border-terminal-border/30">
                <p className="font-cyber text-neon-cyan tracking-[0.2em] mb-4 flex items-center gap-2">
                    <Terminal className="w-4 h-4" /> &gt; {t('subtitle')}
                </p>
                <h1 className="text-4xl md:text-6xl font-display font-black text-foreground drop-shadow-[0_0_15px_rgba(255,255,255,0.1)]">
                    <ScrambleText text={t('title')} />
                </h1>
                <p className="mt-6 text-lg text-muted-foreground font-mono leading-relaxed max-w-2xl">
                    <ScrambleText text={t('meta_description')} revealDelay={500} />
                </p>
            </div>

            {/* Content Sections */}
            
            {/* SECTION 1: Initialization */}
            <section id="getting_started" data-anchor className="scroll-mt-32 relative">
                <div className="absolute -left-8 top-0 bottom-0 w-[1px] bg-gradient-to-b from-matrix-green/50 to-transparent" />
                <h2 className="text-3xl font-display font-bold text-matrix-green mb-6 flex items-center gap-4">
                    <span className="text-sm font-mono opacity-50">01.</span>
                    {t('section_getting_started')}
                </h2>
                
                <div className="space-y-6 text-muted-foreground font-mono leading-relaxed">
                    <h3 className="text-xl text-foreground mt-8 mb-4">{t('doc_install_title')}</h3>
                    <p>{t('doc_install_desc')}</p>
                    
                    <CodeBlock 
                        language="bash"
                        code={`curl -sL https://cybervpn.net/install.sh | bash
sudo systemctl enable cybervpn-core
cybervpn auth --token=YOUR_NEURAL_ID`}
                    />
                    
                    <p>Upon successful initialization, the core daemon will daemonize and establish a local proxy endpoint on <code className="text-neon-cyan bg-neon-cyan/10 px-1 py-0.5 rounded">127.0.0.1:1080</code>.</p>
                </div>
            </section>

            {/* SECTION 2: Routing */}
            <section id="routing" data-anchor className="scroll-mt-32 relative">
                <div className="absolute -left-8 top-0 bottom-0 w-[1px] bg-gradient-to-b from-neon-pink/50 to-transparent" />
                <h2 className="text-3xl font-display font-bold text-neon-pink mb-6 flex items-center gap-4">
                    <span className="text-sm font-mono opacity-50">02.</span>
                    {t('section_routing')}
                </h2>
                
                <div className="space-y-6 text-muted-foreground font-mono leading-relaxed">
                    <h3 className="text-xl text-foreground mt-8 mb-4">{t('doc_config_title')}</h3>
                    <p>{t('doc_config_desc')}</p>
                    
                    <CodeBlock 
                        language="json"
                        code={`{
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
}`}
                    />
                </div>
            </section>

            {/* SECTION 3: Encryption */}
            <section id="security" data-anchor className="scroll-mt-32 relative">
                <div className="absolute -left-8 top-0 bottom-0 w-[1px] bg-gradient-to-b from-neon-cyan/50 to-transparent" />
                <h2 className="text-3xl font-display font-bold text-neon-cyan mb-6 flex items-center gap-4">
                    <span className="text-sm font-mono opacity-50">03.</span>
                    {t('section_security')}
                </h2>
                
                <div className="space-y-6 text-muted-foreground font-mono leading-relaxed">
                    <h3 className="text-xl text-foreground mt-8 mb-4">{t('doc_protocols_title')}</h3>
                    <p>{t('doc_protocols_desc')}</p>
                    
                    <div className="p-4 border border-terminal-border/40 bg-terminal-bg/30 relative overflow-hidden group">
                        <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-neon-cyan to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                        <h4 className="text-neon-cyan mb-2">VLESS + XTLS-Reality</h4>
                        <p className="text-sm">The recommended configuration for maximum DPI evasion. Strips TLS overhead while maintaining perfect forward secrecy via x25519 elliptic curves.</p>
                    </div>
                </div>
            </section>

            {/* SECTION 4: API */}
            <section id="api" data-anchor className="scroll-mt-32 relative">
                <div className="absolute -left-8 top-0 bottom-0 w-[1px] bg-gradient-to-b from-warning/50 to-transparent" />
                <h2 className="text-3xl font-display font-bold text-warning mb-6 flex items-center gap-4">
                    <span className="text-sm font-mono opacity-50">04.</span>
                    {t('section_api')}
                </h2>
                
                <div className="space-y-6 text-muted-foreground font-mono leading-relaxed">
                    <h3 className="text-xl text-foreground mt-8 mb-4">Neural API Interface</h3>
                    <p>Integrate directly with the VPN core using our high-performance gRPC or REST endpoints. Authentication is handled via bearer tokens generated in the dashboard.</p>
                    
                    <CodeBlock 
                        language="typescript"
                        code={`import { CyberVPN } from '@cybervpn/sdk';

const client = new CyberVPN({
  token: process.env.CYBER_NEURAL_TOKEN,
  endpoint: 'api.cybervpn.net/v1'
});

// Connect to the fastest node in standard stealth mode
const session = await client.connect({
  mode: 'stealth',
  region: 'EU-West'
});

console.log('Neural Link Active:', session.ip);`}
                    />
                </div>
            </section>

        </div>
    );
}

// Sub-component for highly interactive Code Blocks
function CodeBlock({ code, language }: { code: string; language: string }) {
    const [copied, setCopied] = useState(false);

    const handleCopy = () => {
        navigator.clipboard.writeText(code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="relative group my-8 overflow-hidden rounded-xl border border-white/10 bg-[#0d0d0d]">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-2 bg-white/5 border-b border-white/5 backdrop-blur-md">
                <span className="text-xs font-mono text-white/50">{language}</span>
                <button 
                    onClick={handleCopy}
                    className="flex items-center gap-2 text-xs font-mono text-white/40 hover:text-white hover:bg-white/10 px-2 py-1 rounded transition-colors"
                >
                    <AnimatePresence mode="wait">
                        {copied ? (
                            <motion.span 
                                key="check"
                                initial={{ opacity: 0, scale: 0.8 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.8 }}
                                className="text-matrix-green flex items-center gap-1"
                            >
                                <Check className="w-3 h-3" /> COPIED
                            </motion.span>
                        ) : (
                            <motion.span 
                                key="copy"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                className="flex items-center gap-1"
                            >
                                <Copy className="w-3 h-3" /> COPY
                            </motion.span>
                        )}
                    </AnimatePresence>
                </button>
            </div>
            
            {/* Body */}
            <div className="p-4 overflow-x-auto relative">
                {/* Glow behind code block */}
                <div className="absolute inset-0 bg-gradient-to-br from-neon-cyan/5 to-transparent pointer-events-none" />
                <pre className="text-sm font-mono text-gray-300 relative z-10">
                    <code>{code}</code>
                </pre>
            </div>
        </div>
    );
}
