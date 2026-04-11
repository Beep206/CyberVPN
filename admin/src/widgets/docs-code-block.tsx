'use client';

import { useState } from 'react';
import { Check, Copy } from 'lucide-react';

export function DocsCodeBlock({
  code,
  language,
}: {
  code: string;
  language: string;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="relative my-8 overflow-hidden rounded-xl border border-white/10 bg-[#0d0d0d]">
      <div className="flex items-center justify-between border-b border-white/5 bg-white/5 px-4 py-2 backdrop-blur-md">
        <span className="text-xs font-mono text-white/50">{language}</span>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-2 rounded px-2 py-1 text-xs font-mono text-white/40 transition-colors hover:bg-white/10 hover:text-white"
        >
          {copied ? (
            <span className="flex items-center gap-1 text-matrix-green">
              <Check className="h-3 w-3" /> COPIED
            </span>
          ) : (
            <span className="flex items-center gap-1">
              <Copy className="h-3 w-3" /> COPY
            </span>
          )}
        </button>
      </div>

      <div className="relative overflow-x-auto p-4">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-neon-cyan/5 to-transparent" />
        <pre className="relative z-10 text-sm font-mono text-gray-300">
          <code>{code}</code>
        </pre>
      </div>
    </div>
  );
}
