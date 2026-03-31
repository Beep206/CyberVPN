'use client';

import { motion } from 'motion/react';
import { Check, Minus } from 'lucide-react';
import { MobileDataList } from '@/shared/ui/mobile-data-list';

const featuresData = [
    { name: "AES-256 Encryption", basic: true, pro: true, elite: true },
    { name: "Zero-Log Policy", basic: true, pro: true, elite: true },
    { name: "Bandwidth Limit", basic: "10 GB", pro: "Unlimited", elite: "Unlimited" },
    { name: "Global Nodes", basic: "5 Regions", pro: "50+ Regions", elite: "Total Access" },
    { name: "Multi-Hop (Double VPN)", basic: false, pro: true, elite: true },
    { name: "Quantum-Resistant Hash", basic: false, pro: true, elite: true },
    { name: "Dedicated IPv4/IPv6", basic: false, pro: false, elite: true },
    { name: "Obfuscated Bridges", basic: false, pro: false, elite: true },
    { name: "Guaranteed 10Gbps Uplink", basic: false, pro: false, elite: true },
];

export function FeatureMatrix() {
    const renderValue = (value: boolean | string, accentClassName: string) => {
        if (typeof value === 'boolean') {
            return value ? (
                <Check className={`w-5 h-5 ${accentClassName}`} />
            ) : (
                <Minus className="w-5 h-5 text-white/20" />
            );
        }

        return <span className={accentClassName}>{value}</span>;
    };

    return (
        <div className="w-full overflow-hidden border border-white/10 bg-black/60 backdrop-blur-xl rounded-2xl p-6 md:p-10">
            <h3 className="text-2xl font-display font-bold tracking-widest text-white uppercase mb-8 flex items-center gap-4">
                <span className="w-2 h-6 bg-neon-cyan inline-block rounded-sm animate-pulse" />
                Feature Matrix Data
            </h3>

            <div className="md:hidden">
                <MobileDataList
                    items={featuresData.map((row) => ({
                        id: row.name,
                        title: row.name,
                        primaryFields: [
                            { label: 'Stealth', value: renderValue(row.basic, 'text-neon-cyan') },
                            { label: 'Cyber_Pro', value: renderValue(row.pro, 'text-matrix-green') },
                            { label: 'Elite_Sync', value: renderValue(row.elite, 'text-neon-purple font-bold drop-shadow-[0_0_5px_rgba(255,0,255,0.5)]') },
                        ],
                    }))}
                />
            </div>

            <div className="hidden md:block w-full overflow-x-auto custom-scrollbar pb-4">
                <table className="w-full min-w-[600px] text-left border-collapse">
                    <thead>
                        <tr className="border-b border-white/10 text-xs font-mono uppercase tracking-widest text-muted-foreground">
                            <th className="py-4 px-4 font-normal w-2/5">Capability</th>
                            <th className="py-4 px-4 font-normal text-center text-neon-cyan">Stealth</th>
                            <th className="py-4 px-4 font-normal text-center text-matrix-green">Cyber_Pro</th>
                            <th className="py-4 px-4 font-normal text-center text-neon-purple">Elite_Sync</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 font-mono text-sm text-white/80">
                        {featuresData.map((row, i) => (
                            <motion.tr 
                                key={row.name}
                                initial={{ opacity: 0, y: 10 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true, margin: "-50px" }}
                                transition={{ delay: i * 0.05 }}
                                className="group hover:bg-white/[0.02] transition-colors"
                            >
                                <td className="py-4 px-4 font-medium">{row.name}</td>
                                
                                <td className="py-4 px-4 text-center">
                                    {renderValue(row.basic, 'text-neon-cyan')}
                                </td>
                                
                                <td className="py-4 px-4 text-center bg-matrix-green/[0.02] group-hover:bg-matrix-green/[0.05] transition-colors">
                                    {renderValue(row.pro, 'text-matrix-green')}
                                </td>
                                
                                <td className="py-4 px-4 text-center">
                                    {renderValue(row.elite, 'text-neon-purple font-bold drop-shadow-[0_0_5px_rgba(255,0,255,0.5)]')}
                                </td>
                            </motion.tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
