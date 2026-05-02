import { motion } from "framer-motion";
import { Activity } from "lucide-react";
import { useTranslation } from "react-i18next";

interface ThreatRadarSVGProps {
  isProbing: boolean;
  threatLevel?: number; // 0 to 100
  logs: string[];
}

export function ThreatRadarSVG({ isProbing, threatLevel = 0 }: ThreatRadarSVGProps) {
  const { t } = useTranslation();
  
  // Base threat color mapping
  const getColor = (level: number) => {
    if (level < 30) return "#00ff88"; // Matrix Green
    if (level < 70) return "#ffaa00"; // Warning Orange
    return "#ff00ff"; // Neon Magenta
  };
  
  const mainColor = getColor(threatLevel);

  return (
    <div className="relative w-full h-full flex flex-col items-center justify-center bg-black/60 rounded-2xl border border-white/10 shadow-[inset_0_0_50px_rgba(0,0,0,0.8)] overflow-hidden">
      {/* Radar SVG */}
      <div className="absolute inset-0 flex items-center justify-center opacity-80 pointer-events-none">
        <svg viewBox="0 0 400 400" className="w-full h-full max-w-[350px]">
          {/* Core Circles */}
          {[1, 2, 3].map((ring) => (
            <motion.circle
              key={ring}
              cx="200"
              cy="200"
              r={ring * 55}
              fill="none"
              stroke={mainColor}
              strokeWidth="1"
              strokeOpacity={0.2 + (ring * 0.1)}
              strokeDasharray={isProbing ? "4 8" : "none"}
              animate={{
                rotate: isProbing ? 360 : 0
              }}
              transition={{
                duration: 20 * ring,
                repeat: Infinity,
                ease: "linear"
              }}
              style={{ originX: "200px", originY: "200px" }}
            />
          ))}

          {/* Sweeper */}
          {isProbing && (
            <motion.path
              d="M200 200 L200 35 A165 165 0 0 1 365 200 Z"
              fill="url(#radarGradient)"
              opacity="0.5"
              animate={{
                rotate: 360
              }}
              transition={{
                duration: 2.5,
                repeat: Infinity,
                ease: "linear"
              }}
              style={{ originX: "200px", originY: "200px" }}
            />
          )}

          {/* Center Hub */}
          <circle cx="200" cy="200" r="8" fill={mainColor} className="animate-pulse shadow-[0_0_15px_currentColor]" />
          
          <defs>
             <radialGradient id="radarGradient">
                <stop offset="0%" stopColor={mainColor} stopOpacity="0.8" />
                <stop offset="100%" stopColor={mainColor} stopOpacity="0" />
             </radialGradient>
          </defs>
        </svg>
      </div>

      <div className="z-10 flex flex-col items-center gap-4 mt-auto mb-8 bg-black/50 p-4 border border-white/10 backdrop-blur-md rounded-xl shadow-lg">
        <h4 className="text-white font-mono uppercase tracking-widest text-sm flex items-center gap-2">
          <Activity size={16} className="animate-pulse" style={{ color: mainColor }} />
          {t('stealthLab.threatLevel')}: <span style={{ color: mainColor }}>{threatLevel}%</span>
        </h4>
        <div className="w-56 h-1.5 bg-gray-900 rounded-full overflow-hidden border border-white/5">
           <motion.div 
             className="h-full shadow-[0_0_10px_currentColor]"
             style={{ backgroundColor: mainColor }}
             initial={{ width: 0 }}
             animate={{ width: `${threatLevel}%` }}
             transition={{ duration: 1.5, ease: "easeOut" }}
           />
        </div>
      </div>
      
      {/* Scanline overlay */}
      <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,255,0.03),rgba(0,255,255,0.02))] bg-[length:100%_4px,3px_100%] opacity-40 z-20" />
    </div>
  );
}
