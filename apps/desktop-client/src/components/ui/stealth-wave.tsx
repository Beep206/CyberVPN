import { useEffect, useRef } from "react";
import { motion } from "framer-motion";

interface StealthWaveProps {
  active: boolean;
  className?: string;
}

export function StealthWave({ active, className = "" }: StealthWaveProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let time = 0;

    const resize = () => {
      const parent = canvas.parentElement;
      canvas.width = parent?.clientWidth || window.innerWidth;
      canvas.height = parent?.clientHeight || 200;
    };
    
    window.addEventListener("resize", resize);
    resize();

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      // When active, the wave becomes chaotic, simulating artificial packet jitter and dynamic padding.
      const lines = active ? 6 : 2;
      const baseAmplitude = active ? 35 : 15;
      const speed = active ? 0.08 : 0.02;
      
      for (let i = 0; i < lines; i++) {
        ctx.beginPath();
        const yOffset = canvas.height / 2;
        
        ctx.moveTo(0, yOffset);
        
        for (let x = 0; x < canvas.width; x++) {
          const noise = active ? Math.sin(x * 0.04 + time * 2.5) * 8 : 0;
          const y = Math.sin(x * 0.01 + time + (i * 1.5)) * baseAmplitude + noise;
          ctx.lineTo(x, yOffset + y);
        }
        
        ctx.strokeStyle = active 
            ? `rgba(0, 255, 136, ${0.1 + (i * 0.15)})`  // Matrix Green
            : `rgba(0, 255, 255, ${0.1 + (i * 0.1)})`;   // Neon Cyan
        ctx.lineWidth = active ? 2 : 1;
        ctx.stroke();
      }
      
      time += speed;
      animationFrameId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(animationFrameId);
    };
  }, [active]);

  return (
    <motion.div 
        className={`w-full h-32 relative overflow-hidden rounded-xl border border-border/50 bg-black/40 backdrop-blur-md shadow-[0_0_15px_rgba(0,0,0,0.5)] ${className}`}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
    >
        {active && (
            <div className="absolute top-2 left-4 text-[var(--color-matrix-green)] font-mono text-xs tracking-widest animate-pulse z-10 pointer-events-none">
                [ STEALTH CAMOUFLAGE ACTIVE : XHTTP JITTER ENGAGED ]
            </div>
        )}
      <canvas ref={canvasRef} className="w-full h-full" />
    </motion.div>
  );
}
