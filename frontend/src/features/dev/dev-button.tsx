"use client";

import { motion } from "motion/react";
import { Terminal } from "lucide-react";
import { useTheme } from "next-themes";
import { cn } from "@/lib/utils";
import { useEffect, useState } from "react";

interface DevButtonProps {
    onClick: () => void;
}

export function DevButton({ onClick }: DevButtonProps) {
    const { resolvedTheme } = useTheme();
    const [mounted, setMounted] = useState(false);

    /* eslint-disable react-hooks/set-state-in-effect -- Dev-only hydration guard */
    useEffect(() => {
        setMounted(true);
    }, []);
    /* eslint-enable react-hooks/set-state-in-effect */

    if (!mounted) return null;

    const isDark = resolvedTheme === 'dark';

    return (
        <motion.button
            className={cn(
                "fixed bottom-4 left-4 z-50 flex h-12 w-12 items-center justify-center rounded-lg backdrop-blur-md overflow-hidden group transition-all duration-300",
                isDark
                    ? "bg-black/80 text-neon-cyan border border-neon-cyan/50 shadow-[0_0_10px_rgba(0,255,255,0.3)]"
                    : "bg-white/50 border border-gray-200 text-gray-500 shadow-lg hover:text-neon-cyan hover:border-neon-cyan/50 hover:bg-neon-cyan/10"
            )}
            whileHover={{
                scale: 1.1,
                boxShadow: isDark ? "0 0 20px rgba(0,255,255,0.6)" : "0 4px 12px rgba(0,0,0,0.1)"
            }}
            whileTap={{ scale: 0.95 }}
            onClick={onClick}
        >
            <div className={cn(
                "absolute inset-0 transition-opacity",
                isDark ? "bg-neon-cyan/10 opacity-0 group-hover:opacity-100" : "bg-transparent"
            )} />

            {/* Scanline effect (Dark mode only) */}
            {isDark && (
                <div className="absolute inset-0 pointer-events-none opacity-20 bg-[linear-gradient(transparent_50%,rgba(0,0,0,0.5)_50%)] bg-[length:100%_4px]" />
            )}

            <Terminal className="h-6 w-6 relative z-10" />

            {/* Glitch overlay on hover (Dark mode only) */}
            {isDark && (
                <motion.div
                    className="absolute inset-0 bg-neon-pink/20 mix-blend-overlay"
                    initial={{ x: "-100%" }}
                    whileHover={{ x: "100%" }}
                    transition={{ duration: 0.5, ease: "linear" }}
                />
            )}
        </motion.button>
    );
}
