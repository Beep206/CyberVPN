'use client';

import { useState, forwardRef, useId } from 'react';
import { motion } from 'motion/react';
import { Eye, EyeOff, AlertCircle, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

interface CyberInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
    label: string;
    error?: string;
    success?: boolean;
    prefix?: string;
}

export const CyberInput = forwardRef<HTMLInputElement, CyberInputProps>(
    ({ label, error, success, prefix = 'input', type = 'text', className, id: propId, onFocus, onBlur, ...props }, ref) => {
        const generatedId = useId();
        const id = propId ?? generatedId;
        const errorId = `${id}-error`;
        const [isFocused, setIsFocused] = useState(false);
        const [showPassword, setShowPassword] = useState(false);
        const isPassword = type === 'password';
        const inputType = isPassword && showPassword ? 'text' : type;

        return (
            <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="space-y-2"
            >
                {/* Label */}
                <label htmlFor={id} className="block text-sm font-mono text-muted-foreground">
                    {label}
                </label>

                {/* Input container */}
                <div
                    className={cn(
                        "relative group",
                        "rounded-lg overflow-hidden",
                        "transition-all duration-300",
                    )}
                >
                    {/* Glow border effect */}
                    <div
                        className={cn(
                            "absolute -inset-0.5 rounded-lg opacity-0 transition-opacity duration-300 blur-sm",
                            isFocused && !error && "opacity-100",
                            error ? "bg-red-500/50 opacity-100" : "bg-neon-cyan/50",
                            success && "bg-matrix-green/50 opacity-100"
                        )}
                    />

                    {/* Input wrapper */}
                    <div
                        className={cn(
                            "relative flex min-w-0 items-center overflow-hidden",
                            "bg-terminal-bg dark:bg-black/60",
                            "border rounded-lg",
                            "transition-colors duration-200",
                            "has-[:focus-visible]:border-neon-cyan has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-neon-cyan/70 has-[:focus-visible]:ring-offset-2 has-[:focus-visible]:ring-offset-terminal-bg has-[:focus-visible]:shadow-[0_0_18px_rgba(0,255,255,0.26)]",
                            error
                                ? "border-red-500"
                                : success
                                    ? "border-matrix-green"
                                    : isFocused
                                        ? "border-neon-cyan"
                                        : "border-grid-line/50 hover:border-grid-line"
                        )}
                    >
                        {/* Terminal prefix */}
                        <span className="shrink-0 pl-3 pr-1.5 py-3 text-[11px] font-mono text-muted-foreground-low select-none whitespace-nowrap sm:pl-4 sm:pr-2 sm:text-xs">
                            root@{prefix}:~$
                        </span>

                        {/* Input field */}
                        <input
                            ref={ref}
                            id={id}
                            type={inputType}
                            aria-invalid={error ? 'true' : undefined}
                            aria-describedby={error ? errorId : undefined}
                            className={cn(
                                "min-w-0 flex-1 bg-transparent py-3 pr-2 sm:pr-4",
                                "text-foreground font-mono text-sm",
                                "placeholder:text-muted-foreground/30",
                                "focus:outline-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-neon-cyan/50",
                                "autofill:bg-transparent",
                                className
                            )}
                            onFocus={(event) => {
                                setIsFocused(true);
                                onFocus?.(event);
                            }}
                            onBlur={(event) => {
                                setIsFocused(false);
                                onBlur?.(event);
                            }}
                            {...props}
                        />

                        {/* Password toggle */}
                        {isPassword && (
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                className="touch-target inline-flex w-11 shrink-0 items-center justify-center px-3 text-muted-foreground hover:text-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-neon-cyan/70"
                                aria-label={showPassword ? 'Hide password' : 'Show password'}
                                aria-pressed={showPassword}
                            >
                                {showPassword ? (
                                    <EyeOff className="h-4 w-4" aria-hidden="true" />
                                ) : (
                                    <Eye className="h-4 w-4" aria-hidden="true" />
                                )}
                            </button>
                        )}

                        {/* Status indicators */}
                        {error && (
                            <div className="shrink-0 px-3 text-red-500" aria-hidden="true">
                                <AlertCircle className="h-4 w-4" />
                            </div>
                        )}
                        {success && !error && (
                            <div className="shrink-0 px-3 text-matrix-green" aria-hidden="true">
                                <Check className="h-4 w-4" />
                            </div>
                        )}
                    </div>
                </div>

                {/* Error message */}
                {error && (
                    <motion.p
                        id={errorId}
                        role="alert"
                        initial={{ opacity: 0, y: -5 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="text-xs text-red-500 font-mono flex items-center gap-1"
                    >
                        <AlertCircle className="h-3 w-3" aria-hidden="true" />
                        {error}
                    </motion.p>
                )}
            </motion.div>
        );
    }
);

CyberInput.displayName = 'CyberInput';
