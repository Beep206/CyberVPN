'use client';

import { useMotionCapability } from '@/shared/hooks/use-motion-capability';
import { useTime } from '@/shared/hooks/use-time';
import { CypherText } from '@/shared/ui/atoms/cypher-text';

interface FooterLiveStripProps {
  encryptionLabel: string;
  encryptionValue: string;
  integrity: string;
  systemLabel: string;
  year: string;
}

export function FooterLiveStrip({
  encryptionLabel,
  encryptionValue,
  integrity,
  systemLabel,
  year,
}: FooterLiveStripProps) {
  const { allowAmbientAnimations } = useMotionCapability();
  const currentTime = useTime();
  const displayTime = allowAmbientAnimations && currentTime ? currentTime : '--:--:--';

  return (
    <>
      <div className="flex items-center text-xs font-cyber text-muted-foreground-low">
        <span className="mr-1">{systemLabel}:</span>
        <CypherText text={integrity} className="text-neon-cyan" loop={allowAmbientAnimations} loopDelay={2000} />
        <span className="mx-2">|</span>
        <span className="mr-1">{encryptionLabel}:</span>
        <CypherText text={encryptionValue} className="text-neon-purple" loop={allowAmbientAnimations} loopDelay={2500} />
      </div>

      <div className="hidden md:block absolute left-1/2 -translate-x-1/2 font-cyber text-sm text-neon-cyan/80">
        {displayTime}
      </div>

      <p className="text-xs font-mono text-muted-foreground-low text-center md:text-right">
        © <span>{year}</span> CyberVPN Inc. All systems operational.
      </p>
    </>
  );
}
