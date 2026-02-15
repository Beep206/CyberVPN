"use client";

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Bell,
    AlertTriangle,
    CheckCircle,
    Info,
    Trash2,
    CheckCheck,
    X,
    MessageSquare,
    Activity,
    Clock,
    ChevronRight,
    ScanLine
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { CypherText } from '@/shared/ui/atoms/cypher-text';
import { MagneticButton } from '@/shared/ui/magnetic-button';

// Enhanced Mock Notifications
const initialNotifications = [
    {
        id: '1',
        title: 'System Alert',
        message: 'High latency detected on SG-1 Server node.',
        type: 'warning',
        time: '2m',
        read: false,
        priority: 'high'
    },
    {
        id: '2',
        title: 'Subscription',
        message: 'Your plan was successfully renewed for 1 month.',
        type: 'success',
        time: '1h',
        read: false,
        priority: 'normal'
    },
    {
        id: '3',
        title: 'Security Notice',
        message: 'New login detected from device "iPhone 15 Pro".',
        type: 'info',
        time: '3h',
        read: true,
        priority: 'high'
    },
    {
        id: '4',
        title: 'Update Available',
        message: 'CyberVPN v2.4.0 is ready to install.',
        type: 'info',
        time: '1d',
        read: true,
        priority: 'low'
    },
];

type Tab = 'all' | 'unread';

export function NotificationDropdown() {
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const [notifications, setNotifications] = useState(initialNotifications);
    const [activeTab, setActiveTab] = useState<Tab>('all');
    const [isScanning, setIsScanning] = useState(false);
    const notificationContainerRef = useRef<HTMLDivElement>(null);
    const [hoveredId, setHoveredId] = useState<string | null>(null);

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

    // Trigger scan effect on open
    useEffect(() => {
        if (isOpen) {
            setIsScanning(true);
            const timer = setTimeout(() => setIsScanning(false), 2000);
            return () => clearTimeout(timer);
        }
    }, [isOpen]);

    const unreadCount = notifications.filter(n => !n.read).length;

    const markAllRead = () => {
        setNotifications(prev => prev.map(n => ({ ...n, read: true })));
    };

    const clearAll = () => {
        setNotifications([]);
    };

    const markAsRead = (id: string) => {
        setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
    };

    const deleteNotification = (id: string) => {
        setNotifications(prev => prev.filter(n => n.id !== id));
    };

    const filteredNotifications = activeTab === 'all'
        ? notifications
        : notifications.filter(n => !n.read);

    return (
        <div className="relative z-50" ref={dropdownRef}>
            <MagneticButton strength={10}>
                <button
                    onClick={() => setIsOpen(!isOpen)}
                    className={cn(
                        "relative flex items-center justify-center w-10 h-10 rounded-xl transition-all duration-500",
                        isOpen
                            ? "bg-neon-cyan/10 text-neon-cyan ring-1 ring-neon-cyan/50 shadow-[0_0_20px_rgba(0,255,255,0.3)]"
                            : "bg-muted/20 text-muted-foreground hover:bg-muted/40 hover:text-foreground"
                    )}
                >
                    <Bell className={cn("w-5 h-5 transition-transform duration-500", isOpen && "rotate-[360deg]")} />

                    {unreadCount > 0 && (
                        <span className="absolute top-2 right-2 flex h-2.5 w-2.5">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neon-pink opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-neon-pink shadow-[0_0_8px_#ff00ff]"></span>
                        </span>
                    )}
                </button>
            </MagneticButton>

            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: 10, scale: 0.95, filter: 'blur(10px)' }}
                        animate={{ opacity: 1, y: 0, scale: 1, filter: 'blur(0px)' }}
                        exit={{ opacity: 0, y: 10, scale: 0.95, filter: 'blur(10px)' }}
                        transition={{ duration: 0.3, ease: "circOut" }}
                        className="absolute right-0 top-full mt-3 w-80 sm:w-[420px] rounded-2xl border border-border/50 dark:border-white/10 bg-background/95 dark:bg-terminal-surface/80 backdrop-blur-3xl shadow-xl dark:shadow-[0_20px_50px_-12px_rgba(0,0,0,0.7)] overflow-hidden ring-1 ring-black/5 dark:ring-white/5 origin-top-right group"
                    >
                        {/* Cyber Scan Effect */}
                        <AnimatePresence>
                            {isScanning && (
                                <motion.div
                                    initial={{ top: '-10%' }}
                                    animate={{ top: '110%' }}
                                    exit={{ opacity: 0 }}
                                    transition={{ duration: 1.5, ease: "linear", repeat: 0 }}
                                    className="absolute left-0 w-full h-20 bg-gradient-to-b from-transparent via-primary/5 dark:via-neon-cyan/10 to-transparent z-0 pointer-events-none"
                                />
                            )}
                        </AnimatePresence>

                        {/* Background Grid */}
                        <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-5 dark:opacity-10 pointer-events-none" />

                        {/* Header */}
                        <div className="relative p-5 border-b border-border/50 dark:border-white/5 bg-muted/40 dark:bg-black/40 backdrop-blur-md z-1">
                            <div className="flex items-center justify-between mb-5">
                                <div className="flex items-center gap-3">
                                    <div className="relative">
                                        <div className="absolute inset-0 bg-neon-cyan/20 blur-lg rounded-full" />
                                        <Activity className="w-5 h-5 text-primary dark:text-neon-cyan relative z-10" />
                                    </div>
                                    <div>
                                        <h3 className="font-bold text-sm tracking-wide text-foreground dark:text-white">System Logs</h3>
                                        <p className="text-[10px] font-mono text-muted-foreground/70 uppercase tracking-wider">
                                            {unreadCount} Unread Events
                                        </p>
                                    </div>
                                </div>

                                <div className="flex items-center gap-1 bg-background/50 dark:bg-white/5 p-1 rounded-lg border border-border/50 dark:border-white/5">
                                    <button
                                        onClick={markAllRead}
                                        className="p-1.5 rounded-md hover:bg-accent dark:hover:bg-white/10 text-muted-foreground hover:text-primary dark:hover:text-neon-cyan transition-all group/btn relative overflow-hidden"
                                        title="Mark all as read"
                                    >
                                        <div className="absolute inset-0 bg-primary/10 dark:bg-neon-cyan/10 translate-y-full group-hover/btn:translate-y-0 transition-transform duration-300" />
                                        <CheckCheck className="w-4 h-4 relative z-10" />
                                    </button>
                                    <div className="w-px h-4 bg-border/50 dark:bg-white/10" />
                                    <button
                                        onClick={clearAll}
                                        className="p-1.5 rounded-md hover:bg-accent dark:hover:bg-white/10 text-muted-foreground hover:text-red-500 dark:hover:text-red-400 transition-all group/btn relative overflow-hidden"
                                        title="Clear all"
                                    >
                                        <div className="absolute inset-0 bg-red-500/10 translate-y-full group-hover/btn:translate-y-0 transition-transform duration-300" />
                                        <Trash2 className="w-4 h-4 relative z-10" />
                                    </button>
                                </div>
                            </div>

                            {/* Tabs */}
                            <div className="flex p-1 bg-background/50 dark:bg-black/40 rounded-xl border border-border/50 dark:border-white/5 relative overflow-hidden">
                                {['all', 'unread'].map((tab) => (
                                    <button
                                        key={tab}
                                        onClick={() => setActiveTab(tab as Tab)}
                                        className={cn(
                                            "flex-1 py-1.5 text-xs font-medium rounded-lg transition-all relative z-10",
                                            activeTab === tab
                                                ? "text-primary-foreground dark:text-white"
                                                : "text-muted-foreground hover:text-foreground/70 dark:hover:text-white/70"
                                        )}
                                    >
                                        {activeTab === tab && (
                                            <motion.div
                                                layoutId="activeTabNotif"
                                                className="absolute inset-0 bg-primary dark:bg-white/10 border border-transparent dark:border-white/5 rounded-lg shadow-sm"
                                                transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                                            />
                                        )}
                                        <span className="relative z-10 capitalize tracking-wide">{tab}</span>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* List */}
                        <div className="relative max-h-[60vh] overflow-y-auto custom-scrollbar bg-background/20 dark:bg-black/20">
                            <AnimatePresence mode='popLayout'>
                                {filteredNotifications.length === 0 ? (
                                    <motion.div
                                        initial={{ opacity: 0, scale: 0.9 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        exit={{ opacity: 0, scale: 0.9 }}
                                        className="flex flex-col items-center justify-center py-16 px-4 text-center"
                                    >
                                        <div className="w-20 h-20 rounded-full bg-gradient-to-b from-muted to-transparent dark:from-white/5 flex items-center justify-center mb-4 border border-border/50 dark:border-white/5 shadow-inner">
                                            <ScanLine className="w-8 h-8 text-muted-foreground/30" />
                                        </div>
                                        <p className="text-sm font-medium text-foreground">All Systems Nominal</p>
                                        <p className="text-xs text-muted-foreground/50 mt-1 max-w-[200px]">
                                            No new events in the log.
                                        </p>
                                    </motion.div>
                                ) : (
                                    filteredNotifications.map((n, index) => (
                                        <motion.div
                                            key={n.id}
                                            layout
                                            initial={{ opacity: 0, x: 20, filter: 'blur(5px)' }}
                                            animate={{ opacity: 1, x: 0, filter: 'blur(0px)' }}
                                            exit={{ opacity: 0, x: -20, filter: 'blur(5px)' }}
                                            transition={{ delay: index * 0.05 }}
                                            onMouseEnter={() => setHoveredId(n.id)}
                                            onMouseLeave={() => setHoveredId(null)}
                                            className={cn(
                                                "relative p-4 border-b border-border/50 dark:border-grid-line/5 transition-all group/item cursor-default overflow-hidden",
                                                !n.read ? "bg-primary/5 dark:bg-neon-cyan/5" : "hover:bg-accent/40 dark:hover:bg-white/5"
                                            )}
                                        >
                                            {/* Holographic Hover Effect */}
                                            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-primary/5 dark:via-white/5 to-transparent opacity-0 group-hover/item:opacity-100 transition-opacity duration-500 pointer-events-none" />

                                            {/* Tech Border Reveal */}
                                            <div className="absolute inset-0 border border-primary/20 dark:border-neon-cyan/20 opacity-0 group-hover/item:opacity-100 transition-all duration-300 scale-95 group-hover/item:scale-100 pointer-events-none rounded-lg" />

                                            {/* Unread Indicator Bar - Pulsing */}
                                            {!n.read && (
                                                <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-primary dark:bg-neon-cyan shadow-[0_0_15px_theme(colors.neon-cyan.DEFAULT)] animate-pulse" />
                                            )}

                                            <div className="flex gap-4 relative z-10">
                                                <div className="mt-1 relative">
                                                    <div className={cn(
                                                        "w-8 h-8 rounded-full flex items-center justify-center border bg-background/50 dark:bg-black/40",
                                                        n.type === 'warning' && "border-yellow-500/30 text-yellow-600 dark:border-neon-yellow/30 dark:text-neon-yellow",
                                                        n.type === 'success' && "border-green-500/30 text-green-600 dark:border-neon-green/30 dark:text-neon-green",
                                                        n.type === 'info' && "border-blue-500/30 text-blue-600 dark:border-neon-cyan/30 dark:text-neon-cyan",
                                                    )}>
                                                        {n.type === 'warning' && <AlertTriangle className="w-4 h-4" />}
                                                        {n.type === 'success' && <CheckCircle className="w-4 h-4" />}
                                                        {n.type === 'info' && <Info className="w-4 h-4" />}
                                                    </div>
                                                </div>

                                                <div className="flex-1 min-w-0 flex gap-3">
                                                    <div className="flex-1 min-w-0">
                                                        <span className={cn(
                                                            "text-sm font-medium transition-colors block mb-0.5",
                                                            !n.read ? "text-foreground dark:text-white" : "text-muted-foreground"
                                                        )}>
                                                            <CypherText text={n.title} trigger={hoveredId === n.id} speed={40} />
                                                        </span>
                                                        <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
                                                            {n.message}
                                                        </p>
                                                    </div>

                                                    <div className="flex flex-col items-end gap-2 flex-shrink-0">
                                                        <span className="text-[10px] font-mono text-muted-foreground/50 flex items-center gap-1">
                                                            <Clock className="w-3 h-3" />
                                                            {n.time}
                                                        </span>

                                                        <div className="flex items-center gap-1 opacity-0 group-hover/item:opacity-100 transition-opacity">
                                                            {!n.read && (
                                                                <button
                                                                    onClick={(e) => {
                                                                        e.stopPropagation();
                                                                        markAsRead(n.id);
                                                                    }}
                                                                    className="p-1.5 rounded-md bg-background/80 dark:bg-white/5 border border-border/50 dark:border-white/10 hover:bg-primary/20 hover:text-primary dark:hover:bg-neon-cyan/20 dark:hover:text-neon-cyan hover:border-primary/50 dark:hover:border-neon-cyan/50 transition-all"
                                                                    title="Mark as read"
                                                                >
                                                                    <CheckCheck className="w-3 h-3" />
                                                                </button>
                                                            )}
                                                            <button
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    deleteNotification(n.id);
                                                                }}
                                                                className="p-1.5 rounded-md bg-background/80 dark:bg-white/5 border border-border/50 dark:border-white/10 hover:bg-red-500/20 hover:text-red-500 dark:hover:text-red-400 hover:border-red-500/50 transition-all"
                                                                title="Remove"
                                                            >
                                                                <X className="w-3 h-3" />
                                                            </button>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </motion.div>
                                    ))
                                )}
                            </AnimatePresence>
                        </div>

                        {/* Footer */}
                        {filteredNotifications.length > 0 && (
                            <div className="p-2 bg-muted/40 dark:bg-black/40 border-t border-border/50 dark:border-white/5 backdrop-blur-md">
                                <Button
                                    variant="ghost"
                                    className="w-full text-xs h-9 hover:bg-accent dark:hover:bg-white/5 hover:text-primary dark:hover:text-neon-cyan group border border-transparent hover:border-border/50 dark:hover:border-white/5 rounded-xl gap-2 transition-all"
                                    onClick={() => { }}
                                >
                                    View Full History
                                    <ChevronRight className="w-3 h-3 opacity-50 group-hover:translate-x-1 transition-transform" />
                                </Button>
                            </div>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
