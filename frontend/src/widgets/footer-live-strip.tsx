'use client';

import { useEffect, useRef, useState } from 'react';
import { useMotionCapability } from '@/shared/hooks/use-motion-capability';
import { CypherText } from '@/shared/ui/atoms/cypher-text';

interface FooterLiveStripProps {
  encryptionLabel: string;
  encryptionValue: string;
  integrity: string;
  systemLabel: string;
}

function formatUtcTime() {
  return `${new Date().toISOString().split('T')[1].split('.')[0]} UTC`;
}

export function FooterLiveStrip({
  encryptionLabel,
  encryptionValue,
  integrity,
  systemLabel,
}: FooterLiveStripProps) {
  const { allowAmbientAnimations } = useMotionCapability();
  const timeRef = useRef<HTMLDivElement>(null);
  const [year] = useState(() => String(new Date().getFullYear()));

  useEffect(() => {
    if (!timeRef.current) {
      return;
    }

    const updateTime = () => {
      if (timeRef.current) {
        timeRef.current.textContent = formatUtcTime();
      }
    };

    updateTime();

    if (!allowAmbientAnimations) {
      return;
    }

    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, [allowAmbientAnimations]);

  return (
    <>
      <div className="flex items-center text-xs font-cyber text-muted-foreground-low">
        <span className="mr-1">{systemLabel}:</span>
        <CypherText text={integrity} className="text-neon-cyan" loop={allowAmbientAnimations} loopDelay={2000} />
        <span className="mx-2">|</span>
        <span className="mr-1">{encryptionLabel}:</span>
        <CypherText text={encryptionValue} className="text-neon-purple" loop={allowAmbientAnimations} loopDelay={2500} />
      </div>

      <div ref={timeRef} className="hidden md:block absolute left-1/2 -translate-x-1/2 font-cyber text-sm text-neon-cyan/80">
        --:--:--
      </div>

      <p className="text-xs font-mono text-muted-foreground-low text-center md:text-right">
        © <span>{year}</span> CyberVPN Inc. All systems operational.
      </p>
    </>
  );
}
