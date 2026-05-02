import { Settings } from "lucide-react";
import { useTranslation } from "react-i18next";

interface StealthConfiguratorProps {
  uTls: string;
  setUTls: (val: string) => void;
  padding: number;
  setPadding: (val: number) => void;
  domainFronting: string;
  setDomainFronting: (val: string) => void;
}

export function StealthConfigurator({
  uTls, setUTls,
  padding, setPadding,
  domainFronting, setDomainFronting
}: StealthConfiguratorProps) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-4 p-6 rounded-2xl border border-white/10 bg-black/40 backdrop-blur-md relative overflow-hidden">
      <h3 className="text-lg font-bold flex items-center gap-2 mb-2 text-white">
        <Settings className="text-[#00ffff]" size={20} /> {t('stealthLab.advancedCookbook')}
      </h3>
      <p className="text-xs text-muted-foreground mb-4">
        {t('stealthLab.advancedCookbookDesc')}
      </p>

      <div className="space-y-5 flex-1 overflow-y-auto pr-2 custom-scrollbar">
        {/* uTLS Options */}
        <div className="space-y-2">
          <label className="text-xs font-mono uppercase tracking-widest text-[#00ffff]">
            {t('stealthLab.uTlsFingerprint')}
          </label>
          <div className="grid grid-cols-2 gap-2">
             {["chrome", "firefox", "safari", "ios"].map(fingerprint => (
               <button
                 key={fingerprint}
                 onClick={() => setUTls(fingerprint)}
                 className={`p-2 text-xs font-mono rounded border transition-colors ${uTls === fingerprint ? "bg-[#00ffff]/20 border-[#00ffff] text-[#00ffff]" : "border-white/10 text-gray-400 hover:border-white/30"}`}
               >
                 {fingerprint.toUpperCase()}
               </button>
             ))}
          </div>
        </div>

        {/* Padding Noise */}
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <label className="text-xs font-mono uppercase tracking-widest text-[#00ffff]">
              {t('stealthLab.paddingPattern')}
            </label>
            <span className="text-xs font-mono text-white">{padding} B</span>
          </div>
          <input 
            type="range" 
            min="0" 
            max="1500" 
            step="100"
            value={padding}
            onChange={(e) => setPadding(parseInt(e.target.value))}
            className="w-full accent-[#00ffff] bg-black/50 appearance-none h-1.5 rounded-full outline-none"
          />
        </div>

        {/* Domain Fronting SNI */}
        <div className="space-y-2">
           <label className="text-xs font-mono uppercase tracking-widest text-[#00ffff]">
              {t('stealthLab.domainFronting')}
           </label>
           <input 
             value={domainFronting}
             onChange={(e) => setDomainFronting(e.target.value)}
             placeholder="e.g. www.cloudflare.com"
             className="w-full bg-black/50 border border-white/10 p-2.5 rounded font-mono text-xs text-white focus:border-[#00ffff] outline-none transition-colors"
           />
        </div>
      </div>
    </div>
  );
}
