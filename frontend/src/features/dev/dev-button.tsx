"use client";

import { motion } from "motion/react";
import { Terminal } from "lucide-react";

interface DevButtonProps {
    onClick: () => void;
}

export function DevButton({ onClick }: DevButtonProps) {
    return (
        <motion.button
            className="fixed bottom-4 left-4 z-50 flex h-12 w-12 items-center justify-center rounded-sm bg-black/80 text-neon-cyan border border-neon-cyan/50 shadow-[0_0_10px_rgba(0,255,255,0.3)] backdrop-blur-md overflow-hidden group"
            whileHover={{ scale: 1.1, boxShadow: "0 0 20px rgba(0,255,255,0.6)" }}
            whileTap={{ scale: 0.95 }}
            onClick={onClick}
        >
            <div className="absolute inset-0 bg-neon-cyan/10 opacity-0 group-hover:opacity-100 transition-opacity" />

            {/* Scanline effect */}
            <div className="absolute inset-0 pointer-events-none opacity-20 bg-[linear-gradient(transparent_50%,rgba(0,0,0,0.5)_50%)] bg-[length:100%_4px]" />

            <Terminal className="h-6 w-6 relative z-10" />

            {/* Glitch overlay on hover */}
            <motion.div
                className="absolute inset-0 bg-neon-pink/20 mix-blend-overlay"
                initial={{ x: "-100%" }}
                whileHover={{ x: "100%" }}
                transition={{ duration: 0.5, ease: "linear" }}
            />
        </motion.button>
    );
}
