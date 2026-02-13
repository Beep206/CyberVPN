'use client';

import { motion } from "motion/react";
import { ServerStatusDot } from "@/shared/ui/atoms/server-status-dot";
import { cn } from "@/lib/utils";
import { useTranslations } from "next-intl";
import type { Server } from "@/entities/server/model/types";

interface ServerCardProps {
    server: Pick<Server, 'id' | 'name' | 'location' | 'status' | 'ip' | 'load' | 'protocol'>;
}

export function ServerCard({ server }: ServerCardProps) {
    const t = useTranslations('ServerCard');
    return (
        <motion.div
            initial={{ opacity: 0, y: 20, rotateX: -10 }}
            animate={{ opacity: 1, y: 0, rotateX: 0 }}
            transition={{
                delay: 0,
                type: "spring",
                stiffness: 100
            }}
            whileHover={{ scale: 1.02 }}
            className={cn(
                "cyber-card relative overflow-hidden rounded-xl p-6",
                "transform-3d perspective-1000 rotate-x-2 hover:rotate-x-0 hover:translate-z-10 transition-transform duration-500 ease-cyber"
            )}
        >
            <div className="flex justify-between items-start mb-4">
                <div>
                    <h3 className="text-lg font-display text-foreground tracking-wider">{server.name}</h3>
                    <p className="text-sm text-muted-foreground font-mono">{server.location}</p>
                </div>
                <ServerStatusDot status={server.status} />
            </div>

            <div className="space-y-2">
                <div className="flex justify-between text-xs font-cyber text-muted-foreground">
                    <span>{t('ip')}</span>
                    <span className="text-neon-cyan">{server.ip}</span>
                </div>
                <div className="flex justify-between text-xs font-cyber text-muted-foreground">
                    <span>{t('protocol')}</span>
                    <span className="uppercase text-neon-purple">{server.protocol}</span>
                </div>

                <div className="mt-4">
                    <div className="flex justify-between text-xs font-mono mb-1">
                        <span>{t('load')}</span>
                        <span className={server.load > 80 ? "text-server-warning" : "text-matrix-green"}>{server.load}%</span>
                    </div>
                    <div className="h-1 w-full bg-muted/20 rounded-full overflow-hidden">
                        <motion.div
                            className={cn(
                                "h-full",
                                server.load > 90 ? "bg-server-offline" :
                                    server.load > 70 ? "bg-server-warning" : "bg-matrix-green"
                            )}
                            initial={{ width: 0 }}
                            animate={{ width: `${server.load}%` }}
                            transition={{ duration: 1, delay: 0.2 }}
                        />
                    </div>
                </div>
            </div>

            {/* Decorative scanline or corner accents */}
            <div className="absolute top-0 right-0 p-2 opacity-50">
                <div className="w-2 h-2 border-t border-r border-neon-cyan" />
            </div>
            <div className="absolute bottom-0 left-0 p-2 opacity-50">
                <div className="w-2 h-2 border-b border-l border-neon-cyan" />
            </div>
        </motion.div>
    );
}
