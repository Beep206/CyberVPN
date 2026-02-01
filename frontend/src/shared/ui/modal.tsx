'use client';

import { useEffect, useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'motion/react';
import { X } from 'lucide-react';

interface ModalProps {
    isOpen: boolean;
    onClose: () => void;
    children: React.ReactNode;
    title?: string;
}

export function Modal({ isOpen, onClose, children, title }: ModalProps) {
    // Ref for the scrollable content container
    const contentRef = useRef<HTMLDivElement>(null);

    // Global scroll capture
    useEffect(() => {
        if (!isOpen) return;

        const handleWheel = (e: WheelEvent) => {
            // If the scroll target is NOT inside the content container (e.g., backdrop or header),
            // manually scroll the content container.
            if (contentRef.current && !contentRef.current.contains(e.target as Node)) {
                contentRef.current.scrollTop += e.deltaY;
            }
        };

        window.addEventListener('wheel', handleWheel);
        return () => window.removeEventListener('wheel', handleWheel);
    }, [isOpen]);

    // Prevent scrolling when modal is open
    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = 'hidden';
            document.documentElement.style.overflow = 'hidden';
            window.dispatchEvent(new Event('lenis:stop'));
        } else {
            document.body.style.overflow = '';
            document.documentElement.style.overflow = '';
            window.dispatchEvent(new Event('lenis:start'));
        }
        return () => {
            document.body.style.overflow = '';
            document.documentElement.style.overflow = '';
            window.dispatchEvent(new Event('lenis:start'));
        };
    }, [isOpen]);

    // Handle Escape key
    useEffect(() => {
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };
        document.addEventListener('keydown', handleEscape);
        return () => document.removeEventListener('keydown', handleEscape);
    }, [onClose]);

    // SSR Safe
    const [mounted, setMounted] = useState(false);
    useEffect(() => setMounted(true), []);

    if (!mounted) return null;

    return createPortal(
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 z-50 bg-black/60 backdrop-blur-md"
                    />

                    {/* Modal Container */}
                    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0, y: 20 }}
                            animate={{ scale: 1, opacity: 1, y: 0 }}
                            exit={{ scale: 0.95, opacity: 0, y: 20 }}
                            transition={{ type: "spring", duration: 0.5, bounce: 0.3 }}
                            className="pointer-events-auto w-full max-w-2xl max-h-[80vh] flex flex-col relative"
                            data-lenis-prevent
                        >
                            {/* Cyberpunk Border Container */}
                            <div className="relative w-full h-full bg-terminal-bg border border-neon-cyan/50 shadow-[0_0_30px_rgba(0,255,255,0.15)] rounded-lg overflow-hidden flex flex-col">

                                {/* Header */}
                                <div className="flex items-center justify-between p-4 border-b border-grid-line/30 bg-terminal-surface/50">
                                    <h2 className="text-xl font-display text-neon-cyan tracking-wider flex items-center gap-2">
                                        <span className="text-neon-pink">►</span>
                                        {title || 'SYSTEM_MODAL'}
                                    </h2>
                                    <button
                                        onClick={onClose}
                                        className="p-2 text-grid-line hover:text-neon-pink transition-colors duration-200"
                                    >
                                        <X size={24} />
                                    </button>
                                </div>

                                {/* Content */}
                                <div
                                    ref={contentRef}
                                    className="flex-1 overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-neon-cyan scrollbar-track-transparent"
                                >
                                    {children}
                                </div>

                                {/* Decor Elements */}
                                <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-neon-cyan" />
                                <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-neon-cyan" />
                                <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-neon-cyan" />
                                <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-neon-cyan" />
                            </div>
                        </motion.div>
                    </div>
                </>
            )}
        </AnimatePresence>,
        document.body
    );
}
