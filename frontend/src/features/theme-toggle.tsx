"use client"

import * as React from "react"
import { Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"

export function ThemeToggle() {
    const { setTheme, theme, systemTheme } = useTheme()
    const [mounted, setMounted] = React.useState(false)

    React.useEffect(() => {
        setMounted(true)
    }, [])

    if (!mounted) {
        return (
            <div className="h-9 w-9 rounded-lg border border-grid-line/30 bg-muted/50" />
        )
    }

    const currentTheme = theme === 'system' ? systemTheme : theme;
    const isDark = currentTheme === 'dark';

    return (
        <button
            onClick={() => setTheme(isDark ? "light" : "dark")}
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-grid-line/30 bg-muted/50 text-muted-foreground hover:text-foreground transition-all hover:bg-accent hover:text-accent-foreground"
            aria-label="Toggle theme"
        >
            {isDark ? (
                <Moon className="h-4 w-4" />
            ) : (
                <Sun className="h-4 w-4 text-orange-400" />
            )}
        </button>
    )
}
