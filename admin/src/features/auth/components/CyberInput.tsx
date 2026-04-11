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
    ({ label, error, success, prefix = 'input', type = 'text', className, id: propId, ...props }, ref) => {
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
                            "relative flex items-center",
                            "bg-terminal-bg dark:bg-black/60",
                            "border rounded-lg",
                            "transition-colors duration-200",
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
                        <span className="pl-4 pr-2 py-3 text-xs font-mono text-muted-foreground-low select-none whitespace-nowrap">
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
                                "flex-1 bg-transparent py-3 pr-4",
                                "text-foreground font-mono text-sm",
                                "placeholder:text-muted-foreground/30",
                                "focus:outline-none",
                                "autofill:bg-transparent",
                                className
                            )}
                            onFocus={() => setIsFocused(true)}
                            onBlur={() => setIsFocused(false)}
                            {...props}
                        />

                        {/* Password toggle */}
                        {isPassword && (
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                className="px-3 text-muted-foreground hover:text-foreground transition-colors"
                                tabIndex={-1}
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
                            <div className="px-3 text-red-500" aria-hidden="true">
                                <AlertCircle className="h-4 w-4" />
                            </div>
                        )}
                        {success && !error && (
                            <div className="px-3 text-matrix-green" aria-hidden="true">
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
