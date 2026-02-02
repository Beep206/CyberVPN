'use client';

import { useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import Link from 'next/link';
import {
    Github,
    Twitter,
    Disc,
    Send,
    ArrowRight,
    Shield,
    Terminal,
    Zap,
    Globe,
    Cpu
} from 'lucide-react';
import { MagneticButton } from '@/shared/ui/magnetic-button';
import { CypherText } from '@/shared/ui/atoms/cypher-text';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { useState, useEffect } from 'react';

const socialLinks = [
    { icon: Twitter, href: '#', label: 'Twitter' },
    { icon: Github, href: '#', label: 'GitHub' },
    { icon: Disc, href: '#', label: 'Discord' },
    { icon: Send, href: '#', label: 'Telegram' },
];

const footerLinks = {
    product: [
        { label: 'features', href: '#features' },
        { label: 'pricing', href: '#pricing' },
        { label: 'servers', href: '#servers' },
        { label: 'download', href: '#download' },
        { label: 'api', href: '#api' },
    ],
    support: [
        { label: 'helpCenter', href: '#' },
        { label: 'status', href: '#' },
        { label: 'contact', href: '#' },
        { label: 'documentation', href: '#' },
    ],
    legal: [
        { label: 'privacy', href: '#' },
        { label: 'terms', href: '#' },
        { label: 'security', href: '#' },
    ]
};

export function Footer() {
    const t = useTranslations('Footer'); // Assuming keys map, or fallback to defaults
    const [hoveredLink, setHoveredLink] = useState<string | null>(null);
    const [dateStr, setDateStr] = useState('');
    const [year, setYear] = useState('');

    useEffect(() => {
        const now = new Date();
        setDateStr(`${now.getFullYear()}.${String(now.getMonth() + 1).padStart(2, '0')}.${String(now.getDate()).padStart(2, '0')}`);
        setYear(String(now.getFullYear()));
    }, []);

    const tHeader = useTranslations('Header'); // Fetch Header translations for system status

    return (
        <footer className="relative w-full bg-terminal-bg border-t border-grid-line/50 overflow-hidden pt-16 pb-8">
            {/* Ambient Background Effects — усилены для light mode */}
            <div className="absolute inset-0 z-0 pointer-events-none">
                <div className="absolute top-0 left-1/4 w-full h-px bg-gradient-to-r from-transparent via-neon-cyan/50 to-transparent opacity-50 blur-[1px]" />
                <div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-neon-purple/10 dark:bg-neon-purple/5 rounded-full blur-[100px]" />
                <div className="absolute top-0 left-0 w-[300px] h-[300px] bg-neon-cyan/10 dark:bg-neon-cyan/5 rounded-full blur-[80px]" />
                <div className="absolute inset-0 bg-[url('/grid-pattern.svg')] opacity-[0.03]" />
            </div>

            <div className="container relative z-10 px-6 mx-auto">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-12 mb-16">

                    {/* Brand Section - Span 4 */}
                    <div className="lg:col-span-4 space-y-6">
                        <Link href="/" className="inline-flex items-center gap-2 group">
                            <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 border border-neon-cyan/30 group-hover:border-neon-cyan/60 transition-colors">
                                <Shield className="h-6 w-6 text-neon-cyan group-hover:animate-pulse" />
                            </div>
                            <span className="font-display text-2xl font-bold tracking-tight text-white group-hover:text-neon-cyan transition-colors">
                                Cyber<span className="text-neon-cyan">VPN</span>
                            </span>
                        </Link>

                        <p className="text-muted-foreground font-mono text-sm leading-relaxed max-w-sm">
                            {t('brandDescription') || "Advanced privacy protection infrastructure for the next generation of the internet. Navigate the digital void with military-grade encryption."}
                        </p>

                        <div className="flex items-center gap-3 pt-2">
                            {socialLinks.map(({ icon: Icon, href, label }) => (
                                <MagneticButton key={label} strength={15}>
                                    <Link
                                        href={href}
                                        className="relative flex h-10 w-10 items-center justify-center rounded-lg border border-grid-line/40 bg-background/50 text-muted-foreground hover:text-neon-cyan hover:border-neon-cyan/50 hover:bg-neon-cyan/10 transition-all duration-300 group"
                                    >
                                        <Icon className="h-4 w-4 group-hover:scale-110 transition-transform" />
                                        <span className="sr-only">{label}</span>
                                        {/* Tooltip-like effect could be added here */}
                                    </Link>
                                </MagneticButton>
                            ))}
                        </div>
                    </div>

                    {/* Links Sections - Span 2 each */}
                    <div className="lg:col-span-2 space-y-6">
                        <h4 className="font-display text-lg font-bold text-foreground flex items-center gap-2">
                            <Terminal className="h-4 w-4 text-neon-purple" />
                            Product
                        </h4>
                        <ul className="space-y-3 font-mono text-sm">
                            {footerLinks.product.map((link) => (
                                <li key={link.label}>
                                    <MagneticButton className="inline-block" strength={10}>
                                        <Link
                                            href={link.href}
                                            className="relative group flex items-center gap-2 text-muted-foreground hover:text-white transition-colors py-1"
                                            onMouseEnter={() => setHoveredLink(link.label)}
                                            onMouseLeave={() => setHoveredLink(null)}
                                        >
                                            <span className={cn(
                                                "w-1.5 h-1.5 rounded-full bg-neon-cyan transition-all duration-300",
                                                hoveredLink === link.label ? "opacity-100 scale-125" : "opacity-0 scale-0"
                                            )} />
                                            <span className={cn("transition-transform duration-300", hoveredLink === link.label ? "translate-x-1" : "")}>
                                                {/* t(`links.${link.label}`) */ link.label.charAt(0).toUpperCase() + link.label.slice(1)}
                                            </span>
                                        </Link>
                                    </MagneticButton>
                                </li>
                            ))}
                        </ul>
                    </div>

                    <div className="lg:col-span-2 space-y-6">
                        <h4 className="font-display text-lg font-bold text-foreground flex items-center gap-2">
                            <Cpu className="h-4 w-4 text-matrix-green" />
                            Support
                        </h4>
                        <ul className="space-y-3 font-mono text-sm">
                            {footerLinks.support.map((link) => (
                                <li key={link.label}>
                                    <MagneticButton className="inline-block" strength={10}>
                                        <Link
                                            href={link.href}
                                            className="relative group flex items-center gap-2 text-muted-foreground hover:text-white transition-colors py-1"
                                            onMouseEnter={() => setHoveredLink(link.label)}
                                            onMouseLeave={() => setHoveredLink(null)}
                                        >
                                            <span className={cn(
                                                "w-1.5 h-1.5 rounded-full bg-matrix-green transition-all duration-300",
                                                hoveredLink === link.label ? "opacity-100 scale-125" : "opacity-0 scale-0"
                                            )} />
                                            <span className={cn("transition-transform duration-300", hoveredLink === link.label ? "translate-x-1" : "")}>
                                                {/* t(`links.${link.label}`) */ link.label.charAt(0).toUpperCase() + link.label.slice(1)}
                                            </span>
                                        </Link>
                                    </MagneticButton>
                                </li>
                            ))}
                        </ul>
                    </div>

                    {/* Newsletter / Newsletter Section - Span 4 */}
                    <div className="lg:col-span-4 space-y-6">
                        <h4 className="font-display text-lg font-bold text-foreground flex items-center gap-2">
                            <Zap className="h-4 w-4 text-warning" />
                            Stay Connected
                        </h4>
                        <p className="text-muted-foreground font-mono text-sm">
                            Join our encrypted frequency. Get updates on server locations, security protocols, and zero-day patches.
                        </p>

                        <div className="relative group">
                            <div className="absolute -inset-0.5 bg-gradient-to-r from-neon-cyan via-neon-purple to-neon-cyan rounded-lg opacity-30 group-hover:opacity-100 transition duration-500 blur group-hover:blur-md animate-gradient-x" />
                            <div className="relative flex gap-2 p-1 bg-terminal-bg rounded-lg border border-grid-line/50">
                                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground/50 font-mono text-xs z-10 select-none">
                                    root@user:~$
                                </span>
                                <Input
                                    className="bg-transparent border-none text-foreground pl-32 focus-visible:ring-0 focus-visible:ring-offset-0 placeholder:text-muted-foreground/30 font-mono h-10"
                                    placeholder="enter_email.exe"
                                />
                                <Button size="sm" className="bg-neon-cyan/10 text-neon-cyan hover:bg-neon-cyan hover:text-black font-mono tracking-wider border border-neon-cyan/20 h-10 px-4 transition-all">
                                    <span className="mr-2">INIT</span>
                                    <ArrowRight className="h-4 w-4" />
                                </Button>
                            </div>
                        </div>

                        <div className="pt-6 flex flex-wrap gap-4 text-xs font-mono text-muted-foreground/60">
                            {footerLinks.legal.map((link) => (
                                <MagneticButton key={link.label} className="inline-block" strength={5}>
                                    <Link
                                        href={link.href}
                                        className="hover:text-neon-cyan transition-colors py-1 px-1"
                                    >
                                        {/* t(`links.${link.label}`) */ link.label.charAt(0).toUpperCase() + link.label.slice(1)}
                                    </Link>
                                </MagneticButton>
                            ))}
                        </div>
                    </div>

                </div>

                {/* Bottom Bar */}
                <div className="pt-8 border-t border-grid-line/20 flex flex-col md:flex-row items-center justify-between gap-4">
                    {/* Cypher Text Status (Moved from Header) */}
                    <div className="flex items-center text-xs font-cyber text-muted-foreground/50">
                        <span className="mr-1">{tHeader('systemLabel')}:</span>
                        <CypherText text={tHeader('integrity')} className="text-neon-cyan" loop loopDelay={2000} />
                        <span className="mx-2">|</span>
                        <span className="mr-1">{tHeader('encryptionLabel')}:</span>
                        <CypherText text={tHeader('encryptionValue')} className="text-neon-purple" loop loopDelay={2500} />
                    </div>

                    <p className="text-xs font-mono text-muted-foreground/40 text-center md:text-right">
                        © <span>{year}</span> CyberVPN Inc. All systems operational.
                    </p>
                </div>
            </div>
        </footer>
    );
}

