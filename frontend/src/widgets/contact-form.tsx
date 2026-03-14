'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { motion, AnimatePresence } from 'motion/react';
import { Mail, User, Building, Send, ShieldAlert, CheckCircle2 } from 'lucide-react';
import { ScrambleText } from '@/shared/ui/scramble-text';
import { MagneticButton } from '@/shared/ui/magnetic-button';
import { Canvas } from '@react-three/fiber';
import { ContactGlobe3D } from '@/3d/scenes/ContactGlobe3D';

export function ContactForm() {
    const t = useTranslations('Contact');
    
    // Form State
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [department, setDepartment] = useState('support');
    const [message, setMessage] = useState('');
    
    // App State for 3D interactions
    const [isTyping, setIsTyping] = useState(false);
    const [isEncrypting, setIsEncrypting] = useState(false);
    const [isSuccess, setIsSuccess] = useState(false);
    const [isHoveringSubmit, setIsHoveringSubmit] = useState(false);
    const [encryptionProgress, setEncryptionProgress] = useState(0);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        
        if (!name || !email || !message) return;
        
        setIsEncrypting(true);
        setIsTyping(false);
        setIsHoveringSubmit(false);
        
        // Simulating the PGP Encryption / Dispatch process
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.floor(Math.random() * 15) + 5;
            if (progress >= 100) {
                progress = 100;
                clearInterval(interval);
                setTimeout(() => {
                    setIsEncrypting(false);
                    setIsSuccess(true);
                }, 800);
            }
            setEncryptionProgress(progress);
        }, 150);
    };

    const handleInputFocus = () => setIsTyping(true);
    const handleInputBlur = () => setIsTyping(false);

    const resetForm = () => {
        setIsSuccess(false);
        setName('');
        setEmail('');
        setMessage('');
        setEncryptionProgress(0);
    };

    return (
        <div className="w-full min-h-[calc(100vh-80px)] flex flex-col lg:flex-row relative bg-terminal-bg">
            
            {/* Left Pane: The Form */}
            <div className="w-full lg:w-1/2 min-h-screen relative z-20 flex p-6 md:p-12 lg:p-24 items-center justify-center">
                
                {/* Visual Glass Box */}
                <div className="w-full max-w-xl relative">
                    {/* Glowing Accent Ring */}
                    <div className="absolute -inset-1 bg-gradient-to-br from-neon-cyan/20 via-transparent to-neon-purple/20 rounded-3xl blur-xl opacity-50" />
                    
                    <div className="relative rounded-3xl border border-white/5 bg-white/[0.02] backdrop-blur-2xl p-8 md:p-12 shadow-2xl overflow-hidden">
                        
                        <div className="mb-10 space-y-2 relative z-10">
                            <h1 className="text-4xl md:text-5xl font-display font-black text-white">
                                <ScrambleText text={t('title')} />
                            </h1>
                            <p className="text-neon-cyan font-mono text-sm tracking-widest uppercase">
                                {t('subtitle')}
                            </p>
                        </div>

                        <AnimatePresence mode="wait">
                            {!isEncrypting && !isSuccess && (
                                <motion.form 
                                    key="form"
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, x: -50 }}
                                    className="space-y-6 relative z-10"
                                    onSubmit={handleSubmit}
                                >
                                    {/* Name Input */}
                                    <div className="space-y-2">
                                        <label className="text-xs font-mono text-muted-foreground-low uppercase tracking-wider pl-1">
                                            {t('form.name')}
                                        </label>
                                        <div className="relative group">
                                            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                                <User className="h-4 w-4 text-white/30 group-focus-within:text-neon-cyan transition-colors" />
                                            </div>
                                            <input 
                                                type="text" 
                                                required
                                                value={name}
                                                onChange={(e) => setName(e.target.value)}
                                                onFocus={handleInputFocus}
                                                onBlur={handleInputBlur}
                                                className="w-full bg-black/40 border border-white/10 rounded-xl pl-12 pr-4 py-3 text-white placeholder:text-white/20 focus:outline-none focus:border-neon-cyan/50 focus:ring-1 focus:ring-neon-cyan/50 transition-all font-mono text-sm"
                                                placeholder="guest_774"
                                            />
                                        </div>
                                    </div>

                                    {/* Email Input */}
                                    <div className="space-y-2">
                                        <label className="text-xs font-mono text-muted-foreground-low uppercase tracking-wider pl-1">
                                            {t('form.email')}
                                        </label>
                                        <div className="relative group">
                                            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                                <Mail className="h-4 w-4 text-white/30 group-focus-within:text-neon-cyan transition-colors" />
                                            </div>
                                            <input 
                                                type="email" 
                                                required
                                                value={email}
                                                onChange={(e) => setEmail(e.target.value)}
                                                onFocus={handleInputFocus}
                                                onBlur={handleInputBlur}
                                                className="w-full bg-black/40 border border-white/10 rounded-xl pl-12 pr-4 py-3 text-white placeholder:text-white/20 focus:outline-none focus:border-neon-cyan/50 focus:ring-1 focus:ring-neon-cyan/50 transition-all font-mono text-sm"
                                                placeholder="secure@proton.me"
                                            />
                                        </div>
                                    </div>

                                    {/* Department Select */}
                                    <div className="space-y-2">
                                        <label className="text-xs font-mono text-muted-foreground-low uppercase tracking-wider pl-1">
                                            {t('form.department')}
                                        </label>
                                        <div className="relative group">
                                            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                                <Building className="h-4 w-4 text-white/30 group-focus-within:text-neon-cyan transition-colors" />
                                            </div>
                                            <select 
                                                value={department}
                                                onChange={(e) => setDepartment(e.target.value)}
                                                onFocus={handleInputFocus}
                                                onBlur={handleInputBlur}
                                                className="w-full bg-black/40 border border-white/10 rounded-xl pl-12 pr-4 py-3 text-white placeholder:text-white/20 focus:outline-none focus:border-neon-cyan/50 focus:ring-1 focus:ring-neon-cyan/50 transition-all appearance-none font-mono text-sm"
                                            >
                                                <option value="support">{t('form.department_support')}</option>
                                                <option value="sales">{t('form.department_sales')}</option>
                                            </select>
                                        </div>
                                    </div>

                                    {/* Message Textarea */}
                                    <div className="space-y-2">
                                        <label className="text-xs font-mono text-muted-foreground-low uppercase tracking-wider pl-1">
                                            {t('form.message')}
                                        </label>
                                        <textarea 
                                            required
                                            value={message}
                                            onChange={(e) => setMessage(e.target.value)}
                                            onFocus={handleInputFocus}
                                            onBlur={handleInputBlur}
                                            rows={4}
                                            className="w-full bg-black/40 border border-white/10 rounded-xl p-4 text-white placeholder:text-white/20 focus:outline-none focus:border-neon-cyan/50 focus:ring-1 focus:ring-neon-cyan/50 transition-all resize-none font-mono text-sm"
                                            placeholder="&lt; BEGIN TRANSMISSION &gt;"
                                        />
                                    </div>

                                    {/* Submit Button */}
                                    <div className="pt-4">
                                        <MagneticButton strength={20} className="w-full block">
                                            <button 
                                                type="submit"
                                                onMouseEnter={() => setIsHoveringSubmit(true)}
                                                onMouseLeave={() => setIsHoveringSubmit(false)}
                                                className="w-full group relative overflow-hidden rounded-xl bg-white/5 border border-white/10 p-4 text-center font-display font-bold text-white transition-all hover:border-neon-cyan/50 hover:bg-neon-cyan/10 hover:shadow-[0_0_30px_rgba(0,255,255,0.2)]"
                                            >
                                                <span className="relative z-10 flex items-center justify-center gap-2">
                                                    {t('form.submit')}
                                                    <Send className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                                                </span>
                                            </button>
                                        </MagneticButton>
                                    </div>
                                </motion.form>
                            )}

                            {/* Encrypting State */}
                            {isEncrypting && (
                                <motion.div 
                                    key="encrypting"
                                    initial={{ opacity: 0, scale: 0.9 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    exit={{ opacity: 0 }}
                                    className="py-20 text-center space-y-6"
                                >
                                    <ShieldAlert className="w-16 h-16 text-warning mx-auto animate-pulse" />
                                    <div className="text-warning font-display text-xl tracking-widest uppercase">
                                        <ScrambleText text="ENCRYPTING PAYLOAD" />
                                    </div>
                                    
                                    <div className="w-full bg-black/50 rounded-full h-2 overflow-hidden border border-white/5">
                                        <div 
                                            className="bg-warning h-full transition-all duration-150 relative"
                                            style={{ width: `${encryptionProgress}%` }}
                                        >
                                            <div className="absolute inset-0 bg-white/20 animate-pulse" />
                                        </div>
                                    </div>
                                    
                                    <div className="font-mono text-xs text-muted-foreground-low">
                                        [ {encryptionProgress}% ] AES-256-GCM Handshake
                                    </div>
                                </motion.div>
                            )}

                            {/* Success State */}
                            {isSuccess && (
                                <motion.div 
                                    key="success"
                                    initial={{ opacity: 0, scale: 0.9 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    className="py-20 text-center space-y-6"
                                >
                                    <div className="relative inline-block">
                                        <div className="absolute inset-0 bg-neon-cyan blur-2xl opacity-30 animate-pulse" />
                                        <CheckCircle2 className="w-20 h-20 text-neon-cyan relative z-10" />
                                    </div>
                                    <div className="space-y-4">
                                        <h2 className="text-2xl font-display font-bold text-white uppercase tracking-widest">
                                            <ScrambleText text={t('form.success')} />
                                        </h2>
                                        <p className="text-muted-foreground font-mono text-sm">
                                            Connection terminated. <br/> Awaiting counter-response.
                                        </p>
                                    </div>
                                    <button 
                                        onClick={resetForm}
                                        className="mt-8 px-6 py-2 border border-white/10 rounded-full text-xs font-mono text-white/50 hover:text-white hover:border-white/30 transition-all"
                                    >
                                        [ INITIATE NEW UPLINK ]
                                    </button>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </div>

            {/* Right Pane: 3D Holographic Scene */}
            <div className="w-full lg:w-1/2 h-[50vh] lg:h-screen sticky top-0 bg-[#050505] overflow-hidden hidden md:block">
                
                {/* Vignette Overlay to blend the edges */}
                <div className="absolute inset-0 pointer-events-none z-10 box-shadow-vignette shadow-[inset_0_0_150px_rgba(0,0,0,0.9)]" />
                <div className="absolute left-0 top-0 bottom-0 w-32 bg-gradient-to-r from-terminal-bg to-transparent z-10" />

                <Canvas camera={{ position: [0, 0, 8], fov: 45 }}>
                    <ContactGlobe3D 
                        isTyping={isTyping} 
                        isEncrypting={isEncrypting} 
                        isSuccess={isSuccess} 
                        isHoveringSubmit={isHoveringSubmit} 
                    />
                </Canvas>
            </div>

        </div>
    );
}
