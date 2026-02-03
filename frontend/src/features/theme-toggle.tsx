"use client"

import * as React from "react"
import { Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"
import { motion } from "motion/react"
import { MagneticButton } from "@/shared/ui/magnetic-button"

export function ThemeToggle() {
    const { setTheme, theme, systemTheme } = useTheme()
    const [mounted, setMounted] = React.useState(false)

    React.useEffect(() => {
        setMounted(true)
    }, [])

    if (!mounted) {
        return (
            <div className="h-10 w-10 rounded-lg border border-grid-line/30 bg-muted/50" />
        )
    }

    const currentTheme = theme === 'system' ? systemTheme : theme;
    const isDark = currentTheme === 'dark';

    return (
        <MagneticButton strength={20}>
            <motion.button
                onClick={async (e) => {
                    const newTheme = isDark ? "light" : "dark";

                    // Check if View Transitions API is supported
                    if (
                        !document.startViewTransition ||
                        window.matchMedia('(prefers-reduced-motion: reduce)').matches
                    ) {
                        setTheme(newTheme);
                        return;
                    }

                    // Get click coordinates
                    const x = e.clientX;
                    const y = e.clientY;

                    // Calculate radius to the farthest corner
                    const endRadius = Math.hypot(
                        Math.max(x, innerWidth - x),
                        Math.max(y, innerHeight - y)
                    );

                    // Start the view transition
                    const transition = document.startViewTransition(async () => {
                        // Use flushSync to ensure DOM updates happen immediately
                        // within the transition callback
                        const { flushSync } = await import('react-dom');
                        flushSync(() => {
                            setTheme(newTheme);
                        });
                    });

                    // Wait for the pseudo-elements to be created
                    await transition.ready;

                    // Animate the circle reveal
                    const animation = document.documentElement.animate(
                        {
                            clipPath: [
                                `circle(0px at ${x}px ${y}px)`,
                                `circle(${endRadius}px at ${x}px ${y}px)`,
                            ],
                        },
                        {
                            duration: 2500,
                            easing: "cubic-bezier(0.23, 1, 0.32, 1)", // ease-cyber
                            pseudoElement: "::view-transition-new(root)",
                        }
                    );

                    // Allow the transition to finish when the animation completes
                    // (Though view transitions usually wait for animations on the pseudo-elements automatically,
                    // this is a safe guard if we needed manual cleanup, but standard API handles it)
                }}
                className="relative flex h-10 w-10 items-center justify-center rounded-lg border border-grid-line/30 bg-terminal-surface/30 text-muted-foreground hover:text-neon-cyan hover:border-neon-cyan/50 hover:bg-neon-cyan/10 transition-colors duration-300"
                whileHover={{ rotate: 180 }}
                transition={{ type: "spring", stiffness: 200, damping: 10 }}
                aria-label="Toggle theme"
            >
                <div className="relative z-10">
                    {isDark ? (
                        <Moon className="h-5 w-5" />
                    ) : (
                        <Sun className="h-5 w-5 text-orange-400" />
                    )}
                </div>
                {/* Glow effect on hover */}
                <motion.div
                    className="absolute inset-0 rounded-lg bg-neon-cyan/20 blur-md opacity-0 hover:opacity-100 transition-opacity duration-300"
                    layoutId="theme-glow"
                />
            </motion.button>
        </MagneticButton>
    )
}
