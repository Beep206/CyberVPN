import { getTranslations } from 'next-intl/server';
import { Check, Shield, Zap } from 'lucide-react';
import { LazyMount } from '@/shared/ui/lazy-mount';
import { Reveal } from '@/shared/ui/reveal';
import { TiltCard } from '@/shared/ui/tilt-card';
import { SpeedTunnelScene } from '@/widgets/speed-tunnel-scene';

interface ServerInfo {
  flag: string;
  id: string;
}

const SERVERS: ServerInfo[] = [
  { id: 'newYork', flag: '🇺🇸' },
  { id: 'frankfurt', flag: '🇩🇪' },
  { id: 'amsterdam', flag: '🇳🇱' },
  { id: 'tokyo', flag: '🇯🇵' },
  { id: 'singapore', flag: '🇸🇬' },
  { id: 'london', flag: '🇬🇧' },
  { id: 'paris', flag: '🇫🇷' },
  { id: 'toronto', flag: '🇨🇦' },
  { id: 'sydney', flag: '🇦🇺' },
  { id: 'seoul', flag: '🇰🇷' },
] as const;

export async function SpeedTunnel() {
  const t = await getTranslations('Landing.speed_tunnel');

  return (
    <section className="relative min-h-screen w-full py-20 overflow-hidden flex flex-col items-center justify-center bg-background">
      <LazyMount
        className="absolute inset-0 z-0 pointer-events-none"
        defer="idle"
        minimumTier="full"
        placeholder={<div className="absolute inset-0 z-0 bg-background" />}
      >
        <SpeedTunnelScene />
      </LazyMount>

      <div className="container relative z-10 px-4">
        <Reveal className="text-center mb-16">
          <h2 className="text-4xl md:text-6xl font-display font-bold text-foreground mb-4 drop-shadow-2xl">
            {t('titleStart')} <span className="text-neon-cyan">{t('titleHighlight')}</span> {t('titleEnd')}
          </h2>
          <p className="text-muted-foreground font-mono text-lg max-w-2xl mx-auto">
            {t('subtitle')}
          </p>
        </Reveal>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
          {SERVERS.map((server, index) => (
            <Reveal key={server.id} delay={index * 0.05} className={index === SERVERS.length - 1 ? 'lg:col-start-2' : undefined}>
              <TiltCard className="p-6 rounded-xl border border-border/50 dark:border-white/10 bg-background/40 backdrop-blur-md hover:border-neon-cyan/50 hover:dark:border-neon-cyan/60 transition-all duration-300 group h-full">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <span className="text-3xl">{server.flag}</span>
                    <div>
                      <h4 className="font-bold font-display text-foreground text-lg">{t(`servers.${server.id}.country`)}</h4>
                      <span className="text-xs text-muted-foreground font-mono uppercase">{t(`servers.${server.id}.city`)}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-green-500/10 border border-green-500/20">
                    <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                    <span className="text-xs font-bold text-green-500 font-mono">{t('online')}</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 mb-4">
                  <div className="p-3 rounded-lg bg-black/20 border border-white/5 flex items-center gap-2">
                    <Zap className="w-4 h-4 text-neon-cyan" />
                    <span className="text-sm font-mono font-bold text-foreground">10 Gbit/s</span>
                  </div>
                  <div className="p-3 rounded-lg bg-black/20 border border-white/5 flex items-center gap-2">
                    <Shield className="w-4 h-4 text-neon-purple" />
                    <span className="text-sm font-mono font-bold text-foreground">XHTTP</span>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-4 border-t border-white/5">
                  <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground group-hover:text-foreground transition-colors">
                    <Check className="w-3 h-3 text-green-500" />
                    <span>{t('featureTorrent')}</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground group-hover:text-foreground transition-colors">
                    <Check className="w-3 h-3 text-green-500" />
                    <span>{t('featureNoAds')}</span>
                  </div>
                </div>
              </TiltCard>
            </Reveal>
          ))}
        </div>
      </div>

      <div className="absolute bottom-0 left-0 w-full flex justify-center z-10 pointer-events-none">
        <div className="w-full h-32 bg-gradient-to-t from-background to-transparent" />
      </div>
    </section>
  );
}
