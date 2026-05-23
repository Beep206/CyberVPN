"use client"

import * as React from "react"
import { Moon, Sun } from "lucide-react"
import { motion } from "motion/react"
import { useTheme } from "@/app/providers/theme-provider"
import { MagneticButton } from "@/shared/ui/magnetic-button"

export function ThemeToggle() {
    const { setTheme, theme, systemTheme } = useTheme()
    const [mounted, setMounted] = React.useState(false)

    React.useEffect(() => {
        setMounted(true)
    }, [])

    if (!mounted) {
        return (
            <div className="touch-target rounded-lg border border-grid-line/30 bg-muted/50" />
        )
    }

    const currentTheme = theme === 'system' ? systemTheme : theme;
    const isDark = currentTheme === 'dark';

    return (
        <MagneticButton strength={20}>
            <motion.button
                onClick={async (e) => {
                    e.preventDefault();
                    const newTheme = isDark ? "light" : "dark";
                    setTheme(newTheme);
                }}
                className="touch-target relative flex items-center justify-center rounded-lg border border-grid-line/30 bg-terminal-surface/30 text-muted-foreground transition-colors duration-300 hover:border-neon-cyan/50 hover:bg-neon-cyan/10 hover:text-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg focus-visible:shadow-[0_0_12px_var(--color-neon-cyan)]"
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
