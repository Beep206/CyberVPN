'use client';

import { OTPInput, OTPInputContext } from 'input-otp';
import { motion } from 'motion/react';
import { Fragment, useContext, useEffect, useState } from 'react';
import { cn } from '@/lib/utils';

interface CyberOtpInputProps {
    value: string;
    onChange: (value: string) => void;
    onComplete?: (value: string) => void;
    maxLength?: number;
    error?: boolean;
}

export function CyberOtpInput({
    value,
    onChange,
    onComplete,
    maxLength = 6,
    error,
}: CyberOtpInputProps) {
    const [isFocused, setIsFocused] = useState(false);

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="group relative flex justify-center w-full"
        >
            {/* Ambient Glow Container */}
            <div
                className={cn(
                    "absolute -inset-4 rounded-xl opacity-0 transition-opacity duration-500 blur-xl",
                    isFocused ? "bg-neon-cyan/20 opacity-100" : "bg-transparent",
                    error && "bg-red-500/20 opacity-100"
                )}
            />

            <OTPInput
                maxLength={maxLength}
                value={value}
                onChange={onChange}
                onComplete={onComplete}
                onFocus={() => setIsFocused(true)}
                onBlur={() => setIsFocused(false)}
                containerClassName="group flex items-center gap-3 has-[:disabled]:opacity-30"
                render={({ slots }) => (
                    <Fragment>
                        <div className="flex gap-3">
                            {slots.slice(0, 3).map((slot, idx) => (
                                <Slot key={idx} {...slot} error={error} />
                            ))}
                        </div>

                        {/* Cyberpunk Separator */}
                        <div className="flex items-center justify-center">
                            <motion.div
                                animate={{ opacity: [0.5, 1, 0.5] }}
                                transition={{ duration: 2, repeat: Infinity }}
                                className={cn(
                                    "w-3 h-1 rounded-full",
                                    error ? "bg-red-500" : "bg-neon-cyan"
                                )}
                            />
                        </div>

                        <div className="flex gap-3">
                            {slots.slice(3).map((slot, idx) => (
                                <Slot key={idx + 3} {...slot} error={error} />
                            ))}
                        </div>
                    </Fragment>
                )}
            />
        </motion.div>
    );
}

function Slot(props: { char: string | null; isActive: boolean; hasFakeCaret: boolean; error?: boolean }) {
    return (
        <div
            className={cn(
                "relative flex h-14 w-12 items-center justify-center rounded-lg border text-xl transition-all duration-300",
                "bg-terminal-bg/80 backdrop-blur-sm",
                "font-mono text-neon-cyan font-bold",
                // Default Border
                "border-grid-line/50",
                // Hover
                "group-hover/slot:border-neon-cyan/50",
                // Active State
                props.isActive && "z-10 border-neon-cyan ring-2 ring-neon-cyan/30 shadow-[0_0_15px_rgba(0,255,255,0.3)]",
                // Error State
                props.error && "border-red-500 text-red-500 ring-red-500/20 shadow-[0_0_15px_rgba(255,0,0,0.3)]",
                // Filled State (not active, not error)
                !props.isActive && props.char && !props.error && "border-neon-cyan/50 bg-neon-cyan/5 text-neon-cyan"
            )}
        >
            {/* Terminal Scanline overlay for each slot */}
            <div className="absolute inset-0 pointer-events-none overflow-hidden rounded-lg opacity-20 scanline" />

            {/* Render Character */}
            <span className="relative z-10 drop-shadow-[0_0_8px_currentColor]">
                {props.char}
            </span>

            {/* Blinking Cursor (Underscore or Block) */}
            {props.hasFakeCaret && (
                <motion.div
                    layoutId="otp-caret"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: [0, 1, 0] }}
                    transition={{
                        duration: 0.8,
                        repeat: Infinity,
                        ease: "linear"
                    }}
                    className={cn(
                        "absolute inset-0 z-0 flex items-end justify-center pb-2 pointer-events-none",
                        props.error ? "text-red-500" : "text-neon-cyan"
                    )}
                >
                    <div className="h-1 w-6 bg-current rounded-sm shadow-[0_0_5px_currentColor]" />
                </motion.div>
            )}
        </div>
    );
}
