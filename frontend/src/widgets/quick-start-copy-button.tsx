'use client';

import { Check, Copy } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

interface QuickStartCopyButtonProps {
  value: string;
}

export function QuickStartCopyButton({ value }: QuickStartCopyButtonProps) {
  const [copied, setCopied] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);

      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      timeoutRef.current = setTimeout(() => {
        setCopied(false);
      }, 2000);
    } catch {
      setCopied(false);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="w-full relative overflow-hidden inline-flex items-center justify-center gap-2 px-4 py-3 bg-neon-cyan/10 border border-neon-cyan/20 text-neon-cyan rounded-lg hover:bg-neon-cyan/20 transition-all font-mono font-semibold group"
    >
      {value}
      {copied ? <Check size={16} /> : <Copy size={16} />}
      <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
    </button>
  );
}
