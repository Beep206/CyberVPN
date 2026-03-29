import { Check, Shield, Zap } from 'lucide-react';
import { LazyMount } from '@/shared/ui/lazy-mount';
import { Reveal } from '@/shared/ui/reveal';
import { TiltCard } from '@/shared/ui/tilt-card';
import { SpeedTunnelScene } from '@/widgets/speed-tunnel-scene';

interface ServerInfo {
  city: string;
  country: string;
  flag: string;
}

const SERVERS: ServerInfo[] = [
  { country: 'USA', flag: '🇺🇸', city: 'New York' },
  { country: 'Germany', flag: '🇩🇪', city: 'Frankfurt' },
  { country: 'Netherlands', flag: '🇳🇱', city: 'Amsterdam' },
  { country: 'Japan', flag: '🇯🇵', city: 'Tokyo' },
  { country: 'Singapore', flag: '🇸🇬', city: 'Singapore' },
  { country: 'United Kingdom', flag: '🇬🇧', city: 'London' },
  { country: 'France', flag: '🇫🇷', city: 'Paris' },
  { country: 'Canada', flag: '🇨🇦', city: 'Toronto' },
  { country: 'Australia', flag: '🇦🇺', city: 'Sydney' },
  { country: 'South Korea', flag: '🇰🇷', city: 'Seoul' },
] as const;

export function SpeedTunnel() {
  return (
    <section className="relative min-h-screen w-full py-20 overflow-hidden flex flex-col items-center justify-center bg-background">
      <LazyMount className="absolute inset-0 z-0 pointer-events-none" placeholder={<div className="absolute inset-0 z-0 bg-background" />}>
        <SpeedTunnelScene />
      </LazyMount>

      <div className="container relative z-10 px-4">
        <Reveal className="text-center mb-16">
          <h2 className="text-4xl md:text-6xl font-display font-bold text-foreground mb-4 drop-shadow-2xl">
            GLOBAL <span className="text-neon-cyan">ULTRASPEED</span> NETWORK
          </h2>
          <p className="text-muted-foreground font-mono text-lg max-w-2xl mx-auto">
            100+ Locations. 10 Gbit/s Channels. Zero Limits.
          </p>
        </Reveal>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
          {SERVERS.map((server, index) => (
            <Reveal key={server.country} delay={index * 0.05} className={index === SERVERS.length - 1 ? 'lg:col-start-2' : undefined}>
              <TiltCard className="p-6 rounded-xl border border-border/50 dark:border-white/10 bg-background/40 backdrop-blur-md hover:border-neon-cyan/50 hover:dark:border-neon-cyan/60 transition-all duration-300 group h-full">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <span className="text-3xl">{server.flag}</span>
                    <div>
                      <h4 className="font-bold font-display text-foreground text-lg">{server.country}</h4>
                      <span className="text-xs text-muted-foreground font-mono uppercase">{server.city}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-green-500/10 border border-green-500/20">
                    <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                    <span className="text-xs font-bold text-green-500 font-mono">ONLINE</span>
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
                    <span>Torrent</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground group-hover:text-foreground transition-colors">
                    <Check className="w-3 h-3 text-green-500" />
                    <span>No-Ads YT</span>
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
