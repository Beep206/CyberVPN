'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Bell, AlertTriangle, CheckCircle, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

// Mock Notifications
const notifications = [
    {
        id: '1',
        title: 'System Alert',
        message: 'High CPU usage detected on Server-02',
        type: 'warning',
        time: '2 min ago',
        read: false,
    },
    {
        id: '2',
        title: 'Backup Complete',
        message: 'Daily system backup finished successfully',
        type: 'success',
        time: '1 hour ago',
        read: false,
    },
    {
        id: '3',
        title: 'New User',
        message: 'User Alice connected from IP 192.168.1.5',
        type: 'info',
        time: '3 hours ago',
        read: true,
    },
];

export function NotificationDropdown() {
    const [isOpen, setIsOpen] = useState(false);
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

    // Close on Escape key
    useEffect(() => {
        if (!isOpen) return;

        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                setIsOpen(false);
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [isOpen]);

    const unreadCount = notifications.filter(n => !n.read).length;

    return (
        <div className="relative" ref={dropdownRef}>
            <Button
                variant="ghost"
                size="icon"
                magnetic={false}
                onClick={() => setIsOpen(!isOpen)}
                aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ''}`}
                aria-expanded={isOpen}
                aria-haspopup="true"
                aria-controls="notification-panel"
                className="relative text-muted-foreground hover:text-neon-cyan hover:bg-neon-cyan/10 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:shadow-[0_0_12px_var(--color-neon-cyan)]"
            >
                <Bell className="h-5 w-5" />
                {unreadCount > 0 && (
                    <span
                        className="absolute top-2 right-2 h-2 w-2 rounded-full bg-neon-pink shadow-[0_0_8px_#ff00ff]"
                        aria-label={`${unreadCount} unread notifications`}
                        role="status"
                    />
                )}
            </Button>

            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        id="notification-panel"
                        role="region"
                        aria-label="Notifications"
                        aria-live="polite"
                        initial={{ opacity: 0, y: 10, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 10, scale: 0.95 }}
                        transition={{ duration: 0.2 }}
                        className="absolute right-0 mt-2 w-80 sm:w-96 rounded-lg border border-grid-line/30 bg-terminal-surface/95 backdrop-blur-xl shadow-xl z-50 overflow-hidden"
                    >
                        <div className="flex items-center justify-between p-4 border-b border-grid-line/30 bg-black/40">
                            <span className="font-display tracking-wide text-neon-cyan">NOTIFICATIONS</span>
                            <span className="text-xs font-mono text-muted-foreground">{unreadCount} UNREAD</span>
                        </div>

                        <div className="max-h-[60vh] overflow-y-auto" role="list" aria-label="Notification list">
                            {notifications.length === 0 ? (
                                <div className="p-8 text-center text-muted-foreground font-mono text-sm">
                                    NO NEW ALERTS
                                </div>
                            ) : (
                                <div className="divide-y divide-grid-line/10">
                                    {notifications.map((notification) => (
                                        <div
                                            key={notification.id}
                                            role="listitem"
                                            tabIndex={0}
                                            aria-label={`${notification.type}: ${notification.title} - ${notification.message}`}
                                            className={cn(
                                                "p-4 hover:bg-white/5 transition-colors cursor-pointer group [content-visibility:auto] [contain-intrinsic-size:auto_76px] focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-neon-cyan focus-visible:bg-neon-cyan/10",
                                                !notification.read && "bg-neon-cyan/5"
                                            )}
                                        >
                                            <div className="flex gap-3">
                                                <div className="mt-1" aria-hidden="true">
                                                    {notification.type === 'warning' && <AlertTriangle className="h-4 w-4 text-neon-yellow" />}
                                                    {notification.type === 'success' && <CheckCircle className="h-4 w-4 text-neon-green" />}
                                                    {notification.type === 'info' && <Info className="h-4 w-4 text-neon-blue" />}
                                                </div>
                                                <div className="flex-1 space-y-1">
                                                    <div className="flex justify-between items-start">
                                                        <p className={cn("text-sm font-medium leading-none", !notification.read ? "text-foreground" : "text-muted-foreground")}>
                                                            {notification.title}
                                                        </p>
                                                        <span className="text-[10px] font-mono text-muted-foreground">{notification.time}</span>
                                                    </div>
                                                    <p className="text-xs text-muted-foreground line-clamp-2">
                                                        {notification.message}
                                                    </p>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        <div className="p-2 border-t border-grid-line/30 bg-black/40">
                            <Button
                                variant="ghost"
                                aria-label="View all notification logs"
                                className="w-full text-xs font-mono hover:text-neon-cyan h-8 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan"
                            >
                                VIEW ALL LOGS
                            </Button>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
