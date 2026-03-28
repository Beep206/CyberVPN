'use client';

import { useState, useRef, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useTranslations } from 'next-intl';
import { Terminal as TerminalIcon, ShieldAlert, CheckCircle2, ChevronRight, Send, RefreshCw } from 'lucide-react';
import { ScrambleText } from '@/shared/ui/scramble-text';
import { createDeterministicRandom } from '@/3d/lib/seeded-random';

type FormStep = 'department' | 'email' | 'message' | 'encrypting' | 'success';

export function ContactTerminal({ terminalName }: { terminalName: string }) {
    const t = useTranslations('Contact');
    
    const [step, setStep] = useState<FormStep>('department');
    const [history, setHistory] = useState<{ query: string; answer: string }[]>([]);
    
    // Form State
    const [department, setDepartment] = useState('');
    const [email, setEmail] = useState('');
    const [message, setMessage] = useState('');
    
    // UI State
    const [inputValue, setInputValue] = useState('');
    const [encryptionProgress, setEncryptionProgress] = useState(0);
    const inputRef = useRef<HTMLInputElement>(null);
    const scrollRef = useRef<HTMLDivElement>(null);
    const scrambleLines = useMemo(() => {
        const random = createDeterministicRandom(157);

        return Array.from({ length: 15 }, () => {
            let line = '';
            for (let i = 0; i < 220; i++) {
                line += Math.floor(random() * 36).toString(36);
            }
            return line;
        });
    }, []);

    // Auto-focus input when step changes
    useEffect(() => {
        if (step !== 'encrypting' && step !== 'success') {
            setTimeout(() => {
                inputRef.current?.focus();
            }, 100);
        }
    }, [step]);

    // Auto-scroll to bottom
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [history, inputValue, step, encryptionProgress]);

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter' && inputValue.trim()) {
            submitStep(inputValue.trim());
        }
    };

    const submitStep = (value: string) => {
        setInputValue('');
        
        if (step === 'department') {
            const validDepartments = ['support', 'sales', 'press'];
            const mappedValue = value.toLowerCase();
            
            if (validDepartments.includes(mappedValue)) {
                setHistory([...history, { query: 'Select department (support/sales/press):', answer: value }]);
                setDepartment(mappedValue);
                setStep('email');
            } else {
                setHistory([...history, { query: 'Select department (support/sales/press):', answer: `${value} - [ERROR] Invalid Selection` }]);
            }
            return;
        }

        if (step === 'email') {
            if (value.includes('@') && value.includes('.')) {
                setHistory([...history, { query: 'Provide identification (Email):', answer: value }]);
                setEmail(value);
                setStep('message');
            } else {
                setHistory([...history, { query: 'Provide identification (Email):', answer: `${value} - [ERROR] Invalid Format` }]);
            }
            return;
        }

        if (step === 'message') {
            setHistory([...history, { query: 'Enter transmission data (Message):', answer: value }]);
            setMessage(value);
            setStep('encrypting');
            startEncryption();
            return;
        }
    };

    const startEncryption = () => {
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.floor(Math.random() * 15) + 5;
            if (progress >= 100) {
                progress = 100;
                clearInterval(interval);
                setTimeout(() => setStep('success'), 800);
            }
            setEncryptionProgress(progress);
        }, 200);
    };

    const resetTerminal = () => {
        setStep('department');
        setHistory([]);
        setDepartment('');
        setEmail('');
        setMessage('');
        setEncryptionProgress(0);
    };

    return (
        <div className="w-full rounded-xl border border-terminal-border/40 bg-[#0a0a0d]/90 backdrop-blur-xl shadow-[0_0_50px_rgba(0,255,255,0.05)] overflow-hidden relative group">
            {/* Ambient CRT Glow */}
            <div className="absolute inset-0 bg-gradient-to-b from-transparent to-neon-cyan/5 opacity-50 pointer-events-none" />
            
            {/* CRT Scanline Overlay */}
            <div className="absolute inset-0 pointer-events-none opacity-[0.03] bg-[linear-gradient(transparent_50%,rgba(0,0,0,1)_50%)] bg-[length:100%_4px] z-20" />

            {/* Terminal Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-terminal-border/40 bg-white/5">
                <div className="flex gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500/80 border border-red-500" />
                    <div className="w-3 h-3 rounded-full bg-yellow-500/80 border border-yellow-500" />
                    <div className="w-3 h-3 rounded-full bg-green-500/80 border border-green-500" />
                </div>
                <div className="text-xs font-mono text-muted-foreground-low flex items-center gap-2">
                    <TerminalIcon className="w-3 h-3" />
                    {terminalName}
                </div>
                <div className="w-16" /> {/* Spacer for centering */}
            </div>

            {/* Terminal Body */}
            <div 
                ref={scrollRef}
                className="p-6 md:p-8 font-mono text-sm md:text-base h-[60vh] min-h-[400px] overflow-y-auto no-scrollbar relative z-10 space-y-4"
                onClick={() => inputRef.current?.focus()}
            >
                {/* Intro Text */}
                <div className="text-matrix-green mb-6 animate-pulse opacity-80">
                    <p>CyberVPN Core Relay v2.4.1</p>
                    <p>Establishing secure socket... [OK]</p>
                    <p>Initializing PGP handshake... [OK]</p>
                    <p className="mt-2 text-foreground">Type your responses and hit [ENTER]</p>
                </div>

                {/* History Log */}
                {history.map((record, idx) => (
                    <div key={idx} className="space-y-2">
                        <div className="text-muted-foreground">{record.query}</div>
                        <div className="flex items-center gap-2 text-neon-cyan pb-2 border-b border-white/5">
                            <span className="opacity-50">&gt;</span>
                            <span className={record.answer.includes('[ERROR]') ? 'text-red-400' : ''}>
                                {record.answer}
                            </span>
                        </div>
                    </div>
                ))}

                {/* Active Input Area */}
                <AnimatePresence mode="wait">
                    {step === 'department' && (
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-2">
                            <div className="text-foreground">Select department:</div>
                            <div className="flex items-center gap-2 text-muted-foreground-low text-xs mb-2">
                                <span className="bg-white/10 px-1 py-0.5 rounded cursor-pointer hover:text-white" onClick={() => submitStep('support')}>support</span>
                                <span className="bg-white/10 px-1 py-0.5 rounded cursor-pointer hover:text-white" onClick={() => submitStep('sales')}>sales</span>
                                <span className="bg-white/10 px-1 py-0.5 rounded cursor-pointer hover:text-white" onClick={() => submitStep('press')}>press</span>
                            </div>
                            <InputField value={inputValue} onChange={setInputValue} onKeyDown={handleKeyDown} inputRef={inputRef} />
                        </motion.div>
                    )}

                    {step === 'email' && (
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-2">
                            <div className="text-foreground">Provide identification (Email):</div>
                            <InputField value={inputValue} onChange={setInputValue} onKeyDown={handleKeyDown} inputRef={inputRef} type="email" />
                        </motion.div>
                    )}

                    {step === 'message' && (
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-2">
                            <div className="text-foreground">Enter transmission data (Message):</div>
                            <InputField value={inputValue} onChange={setInputValue} onKeyDown={handleKeyDown} inputRef={inputRef} />
                        </motion.div>
                    )}

                    {/* Encryption State */}
                    {step === 'encrypting' && (
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4 py-8 text-center border border-warning/20 bg-warning/5 rounded-lg">
                            <ShieldAlert className="w-8 h-8 text-warning mx-auto animate-pulse" />
                            <div className="text-warning font-display tracking-widest uppercase">
                                Encrypting Payload
                            </div>
                            
                            {/* Raw Data Scramble simulation */}
                            <div className="text-xs text-muted-foreground-low break-all h-20 overflow-hidden opacity-30 select-none">
                                {scrambleLines.map((line, i) => (
                                    <div key={i}>{line}</div>
                                ))}
                            </div>

                            {/* Progress Bar */}
                            <div className="w-3/4 max-w-md mx-auto h-1 bg-white/10 rounded overflow-hidden">
                                <div 
                                    className="h-full bg-warning transition-all duration-200"
                                    style={{ width: `${encryptionProgress}%` }}
                                />
                            </div>
                            <div className="text-xs text-warning/70">
                                RSA-4096 / AES-256-GCM [{encryptionProgress}%]
                            </div>
                        </motion.div>
                    )}

                    {/* Success State */}
                    {step === 'success' && (
                        <motion.div 
                            initial={{ opacity: 0, scale: 0.95 }} 
                            animate={{ opacity: 1, scale: 1 }} 
                            className="space-y-6 py-12 text-center"
                        >
                            <div className="relative inline-flex items-center justify-center">
                                <div className="absolute inset-0 bg-neon-cyan blur-2xl opacity-20" />
                                <CheckCircle2 className="w-16 h-16 text-neon-cyan relative z-10" />
                            </div>
                            
                            <div className="space-y-2">
                                <h3 className="text-2xl font-display font-bold text-white tracking-widest">
                                    <ScrambleText text="TRANSMISSION SUCCESSFUL" />
                                </h3>
                                <p className="text-muted-foreground">
                                    Data packet dispatched. Trace deleted.
                                </p>
                            </div>

                            <button 
                                onClick={resetTerminal}
                                className="group mx-auto flex items-center gap-2 text-sm text-neon-cyan border border-neon-cyan/30 bg-neon-cyan/5 px-6 py-2 rounded-lg hover:bg-neon-cyan/20 transition-colors"
                            >
                                <RefreshCw className="w-4 h-4 group-hover:rotate-180 transition-transform duration-500" />
                                NEW TRANSMISSION
                            </button>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}

// Sub-component for input line
function InputField({ 
    value, 
    onChange, 
    onKeyDown, 
    inputRef,
    type = "text"
}: { 
    value: string; 
    onChange: (v: string) => void; 
    onKeyDown: (e: React.KeyboardEvent<HTMLInputElement>) => void;
    inputRef: React.RefObject<HTMLInputElement | null>;
    type?: string;
}) {
    return (
        <div className="flex items-center gap-2 group relative">
            <span className="text-neon-cyan animate-pulse">&gt;</span>
            <input 
                ref={inputRef}
                type={type}
                value={value}
                onChange={(e) => onChange(e.target.value)}
                onKeyDown={onKeyDown}
                className="bg-transparent border-none outline-none flex-1 text-neon-cyan placeholder:text-neon-cyan/20"
                autoComplete="off"
                spellCheck={false}
            />
            
            {/* Blinking Cursor Simulation (hidden when typing natively handles cursor, but adds flavor) */}
            <div className={`w-2 h-4 bg-neon-cyan/50 animate-pulse ${value ? 'hidden' : 'block'}`} />

            {/* Helper text on desktop */}
            <div className="absolute right-0 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity flex items-center gap-2 text-xs text-muted-foreground-low">
                <span>Press Enter to</span>
                <Send className="w-3 h-3" />
            </div>
        </div>
    );
}
