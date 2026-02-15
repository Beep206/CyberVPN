import { useState, useRef, useEffect } from 'react';
import {
    LayoutDashboard,
    Settings,
    UserCircle,
    LogOut,
    ChevronRight,
    Sparkles,
    CreditCard,
    Shield
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import NextLink from 'next/link';
import { useRouter } from 'next/navigation';
import { MagneticButton } from '@/shared/ui/magnetic-button';
import { useAuthStore } from '@/stores/auth-store';
import { CypherText } from '@/shared/ui/atoms/cypher-text';
import { Link } from '@/i18n/navigation';
import { cn } from '@/lib/utils';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';

export function UserMenu() {
    const [isOpen, setIsOpen] = useState(false);
    const router = useRouter();
    const { user, logout } = useAuthStore();
    const [hoveredItem, setHoveredItem] = useState<string | null>(null);

    const dropdownRef = useRef<HTMLDivElement>(null);

    // Close on click outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleLogout = async () => {
        await logout();
        setIsOpen(false);
        router.push('/');
    };

    // User initials for avatar fallback
    const initials = user?.email
        ? user.email.substring(0, 2).toUpperCase()
        : user?.login?.substring(0, 2).toUpperCase() || 'U';

    const menuItems = [
        {
            icon: LayoutDashboard,
            label: 'Dashboard',
            href: '/dashboard',
            color: 'text-neon-cyan',
            desc: 'Overview & Stats'
        },
        {
            icon: UserCircle,
            label: 'Profile',
            href: '/profile',
            color: 'text-neon-purple',
            desc: 'Account Details'
        },
        {
            icon: Shield,
            label: 'Security',
            href: '/security',
            color: 'text-matrix-green',
            desc: '2FA & Password'
        },
        {
            icon: CreditCard,
            label: 'Billing',
            href: '/billing',
            color: 'text-neon-yellow',
            desc: 'Manage Plan'
        },
        {
            icon: Settings,
            label: 'Settings',
            href: '/settings',
            color: 'text-muted-foreground',
            desc: 'App Preferences'
        },
    ];

    return (
        <div className="relative z-50" ref={dropdownRef}>
            <MagneticButton strength={10}>
                <button
                    onClick={() => setIsOpen(!isOpen)}
                    className={cn(
                        "flex items-center gap-2 p-1 pl-2 pr-1 rounded-full border transition-all duration-300 group relative overflow-hidden",
                        isOpen
                            ? "bg-muted/40 border-neon-cyan/50 ring-2 ring-neon-cyan/20"
                            : "bg-muted/20 border-transparent hover:bg-muted/40 hover:border-white/10"
                    )}
                >
                    <span className="text-xs font-medium max-w-[100px] truncate hidden md:block z-10 relative">
                        {user?.login || user?.email?.split('@')[0]}
                    </span>

                    {/* Status Dot */}
                    <span className="absolute left-2 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-matrix-green shadow-[0_0_8px_theme(colors.matrix-green.DEFAULT)] animate-pulse" />

                    <div className="relative group-hover:scale-105 transition-transform duration-300">
                        <Avatar className="h-8 w-8 border border-white/10 group-hover:border-neon-cyan/50 transition-colors">
                            <AvatarFallback className="bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 text-foreground font-bold text-xs backdrop-blur-md">
                                {initials}
                            </AvatarFallback>
                        </Avatar>
                        {/* Glitch Effect Content would go here if using image, for fallback we use gradient */}
                    </div>
                </button>
            </MagneticButton>

            <AnimatePresence>
                {isOpen && (
                    <>
                        <motion.div
                            initial={{ opacity: 0, y: 10, scale: 0.95, filter: 'blur(10px)' }}
                            animate={{ opacity: 1, y: 0, scale: 1, filter: 'blur(0px)' }}
                            exit={{ opacity: 0, y: 10, scale: 0.95, filter: 'blur(10px)' }}
                            transition={{ duration: 0.2, ease: "circOut" }}
                            className="absolute right-0 top-full mt-3 z-50 w-72 bg-background/95 dark:bg-terminal-surface/80 border border-border/50 dark:border-white/10 rounded-2xl shadow-xl dark:shadow-[0_20px_50px_-12px_rgba(0,0,0,0.7)] backdrop-blur-3xl overflow-hidden ring-1 ring-black/5 dark:ring-white/5"
                        >
                            {/* Cyber Header - Kept distinctive for profile identity, but with adjusted opacity for light mode */}
                            <div className="relative p-5 overflow-hidden group bg-foreground/5 dark:bg-transparent">
                                <div className="absolute inset-0 bg-gradient-to-br from-neon-cyan/10 via-transparent to-neon-purple/10 opacity-50" />
                                <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-10 dark:opacity-20" />

                                {/* Animated scanline */}
                                <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-primary/20 dark:via-white/20 to-transparent animate-scan" />

                                <div className="relative z-10 flex items-center gap-4">
                                    <div className="relative">
                                        <div className="absolute -inset-1 bg-gradient-to-r from-neon-cyan to-neon-purple rounded-full opacity-75 blur-sm group-hover:opacity-100 transition-opacity duration-500" />
                                        <Avatar className="h-12 w-12 border-2 border-background dark:border-black relative">
                                            <AvatarFallback className="bg-zinc-900 text-white font-bold text-lg">
                                                {initials}
                                            </AvatarFallback>
                                        </Avatar>
                                        <div className="absolute bottom-0 right-0 w-3.5 h-3.5 bg-matrix-green border-2 border-background dark:border-black rounded-full shadow-[0_0_8px_theme(colors.matrix-green.DEFAULT)]" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <h4 className="font-bold text-sm text-foreground truncate flex items-center gap-2">
                                            {user?.login}
                                            <Sparkles className="w-3 h-3 text-neon-yellow animate-pulse" />
                                        </h4>
                                        <p className="text-xs text-muted-foreground truncate font-mono opacity-80">
                                            {user?.email}
                                        </p>
                                        <div className="mt-1.5 flex items-center gap-2">
                                            <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20">
                                                PRO
                                            </span>
                                            <span className="text-[10px] text-muted-foreground/50 font-mono">
                                                ID: {user?.id?.substring(0, 4)}...
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Menu Items */}
                            <div className="p-2 space-y-0.5 relative">
                                {menuItems.map((item, index) => (
                                    <div key={item.href}>
                                        <Link
                                            href={item.href}
                                            onClick={() => setIsOpen(false)}
                                            prefetch={false}
                                            onMouseEnter={() => setHoveredItem(item.href)}
                                            onMouseLeave={() => setHoveredItem(null)}
                                            className="relative flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-300 group/item overflow-hidden"
                                        >
                                            {hoveredItem === item.href && (
                                                <motion.div
                                                    layoutId="menuHover"
                                                    className="absolute inset-0 bg-gradient-to-r from-accent/80 via-accent/40 to-transparent dark:from-white/10 dark:via-white/5 dark:to-transparent"
                                                    initial={{ opacity: 0 }}
                                                    animate={{ opacity: 1 }}
                                                    exit={{ opacity: 0 }}
                                                    transition={{ duration: 0.2, ease: "circOut" }}
                                                />
                                            )}

                                            <div className={cn(
                                                "relative z-10 p-2 rounded-lg transition-all duration-300 border",
                                                "bg-muted/50 dark:bg-black/20 group-hover/item:bg-background dark:group-hover/item:bg-black/80",
                                                "border-border/50 dark:border-white/5 group-hover/item:border-primary/50 dark:group-hover/item:border-white/20",
                                                "group-hover/item:scale-110 group-hover/item:rotate-3 group-hover/item:shadow-[0_0_15px_-5px_currentColor]",
                                                item.color.replace('text-', 'text-opacity-80 ')
                                            )}>
                                                <item.icon className={cn("w-4 h-4 transition-transform duration-300", item.color)} />
                                            </div>

                                            <div className="flex-1 relative z-10">
                                                <div className="flex items-center justify-between">
                                                    <span className="text-sm font-medium text-muted-foreground group-hover/item:text-foreground group-hover/item:translate-x-1 transition-all duration-300 flex items-center gap-2">
                                                        <CypherText text={item.label} trigger={hoveredItem === item.href} speed={40} />
                                                    </span>
                                                    <ChevronRight className="w-3 h-3 text-primary dark:text-neon-cyan opacity-0 -translate-x-2 group-hover/item:opacity-100 group-hover/item:translate-x-0 transition-all duration-300 ease-out" />
                                                </div>
                                                <p className="text-[10px] text-muted-foreground/50 font-mono group-hover/item:text-muted-foreground/80 transition-colors delay-75">
                                                    {item.desc}
                                                </p>
                                            </div>
                                        </Link>
                                        {index < menuItems.length - 1 && (
                                            <div className="mx-4 my-1 border-b border-dashed border-border/40 dark:border-white/20" />
                                        )}
                                    </div>
                                ))}
                            </div>

                            {/* Footer */}
                            <div className="p-2 border-t border-border/50 dark:border-white/5 mt-1 bg-muted/30 dark:bg-black/20">
                                <button
                                    onClick={handleLogout}
                                    className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl text-sm font-medium text-muted-foreground hover:bg-red-50 hover:text-red-600 dark:text-red-400 dark:hover:bg-red-500/10 dark:hover:text-red-300 transition-all group"
                                >
                                    <LogOut className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
                                    <span>Sign Out</span>
                                </button>
                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </div>
    );
}
