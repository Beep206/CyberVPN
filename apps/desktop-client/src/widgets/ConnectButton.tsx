
import { motion } from 'framer-motion';
import { Shield, ShieldAlert, ShieldCheck } from 'lucide-react';
import { ConnectionStatus } from '@/shared/api/ipc';
import { useTranslation } from 'react-i18next';

interface ConnectButtonProps {
    status: ConnectionStatus;
    onConnect: () => void;
    onDisconnect: () => void;
}

export function ConnectButton({ status, onConnect, onDisconnect }: ConnectButtonProps) {
    const { t } = useTranslation();
    const isConnected = status.status === "connected";
    const isConnecting = status.status === "connecting";

    const getStatusColor = () => {
        if (isConnected) return "var(--color-matrix-green)";
        if (isConnecting) return "var(--color-neon-cyan)";
        return "var(--muted-foreground)";
    };

    const getIcon = () => {
        if (isConnected) return <ShieldCheck size={48} />;
        if (isConnecting) return <Shield size={48} className="animate-pulse" />;
        return <ShieldAlert size={48} />;
    };

    const handleClick = () => {
        if (isConnected || isConnecting) {
            onDisconnect();
        } else {
            onConnect();
        }
    };

    return (
        <div className="flex flex-col items-center justify-center gap-6">
            <motion.button
                onClick={handleClick}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="relative flex items-center justify-center w-48 h-48 rounded-full border-4 shadow-2xl transition-all duration-500 overflow-hidden group"
                style={{
                    borderColor: getStatusColor(),
                    boxShadow: isConnected || isConnecting ? `0 0 40px ${getStatusColor()}40` : 'none',
                    backgroundColor: 'rgba(0,0,0,0.4)',
                }}
            >
                {/* Background glow effect */}
                <div 
                    className="absolute inset-0 opacity-20 transition-opacity duration-500 group-hover:opacity-40"
                    style={{ backgroundColor: getStatusColor() }} 
                />

                <motion.div 
                    className="relative z-10 flex flex-col items-center gap-2"
                    style={{ color: getStatusColor() }}
                    animate={{ y: isConnecting ? [0, -5, 0] : 0 }}
                    transition={{ repeat: isConnecting ? Infinity : 0, duration: 1 }}
                >
                    {getIcon()}
                    <span className="font-bold tracking-widest uppercase text-sm">
                        {t(`dashboard.status_${status.status}`, { defaultValue: status.status })}
                    </span>
                </motion.div>
                
                {/* Rings */}
                {isConnected && (
                    <>
                       <motion.div 
                          className="absolute inset-0 rounded-full border-2 border-dashed opacity-30"
                          style={{ borderColor: getStatusColor() }}
                          animate={{ rotate: 360 }}
                          transition={{ repeat: Infinity, duration: 8, ease: "linear" }}
                       />
                       <motion.div 
                          className="absolute inset-2 rounded-full border border-dotted opacity-20"
                          style={{ borderColor: getStatusColor() }}
                          animate={{ rotate: -360 }}
                          transition={{ repeat: Infinity, duration: 12, ease: "linear" }}
                       />
                    </>
                )}
            </motion.button>
            
            {(isConnected || isConnecting) && status.activeId && (
                <div className="text-sm font-mono text-muted-foreground bg-black/40 px-4 py-2 rounded-md border border-border/40">
                    {t('dashboard.profileId')}: <span className="text-[var(--color-neon-cyan)]">{status.activeId}</span>
                </div>
            )}
        </div>
    );
}
