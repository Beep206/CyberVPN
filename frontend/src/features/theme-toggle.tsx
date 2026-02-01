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
                onClick={() => setTheme(isDark ? "light" : "dark")}
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
