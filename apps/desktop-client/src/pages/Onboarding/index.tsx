import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { Shield, Zap, QrCode, ArrowRight, CheckCircle, Network } from "lucide-react";

export function OnboardingPage() {
    const navigate = useNavigate();
    const [step, setStep] = useState(1);

    const finishOnboarding = () => {
        localStorage.setItem("onboarding_complete", "true");
        navigate("/");
    };

    const variants = {
        enter: (direction: number) => {
            return {
                x: direction > 0 ? 300 : -300,
                opacity: 0
            };
        },
        center: {
            zIndex: 1,
            x: 0,
            opacity: 1
        },
        exit: (direction: number) => {
            return {
                zIndex: 0,
                x: direction < 0 ? 300 : -300,
                opacity: 0
            };
        }
    };

    return (
        <div className="flex h-screen w-full bg-[#0a0f12] text-white overflow-hidden items-center justify-center relative font-sans">
            <div className="absolute inset-0 z-0 bg-black/60 point-events-none" />
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-[#00ff88]/5 rounded-full blur-[100px] pointer-events-none" />
            
            <div className="relative z-10 w-full max-w-2xl bg-black/50 border border-white/5 backdrop-blur-md rounded-2xl shadow-2xl p-10 flex flex-col items-center">
                <div className="flex justify-center gap-4 mb-10 w-full">
                    {[1, 2, 3].map((s) => (
                        <div key={s} className={`h-1.5 w-1/4 rounded-full transition-all duration-500 ${step >= s ? "bg-[#00ff88] shadow-[0_0_10px_rgba(0,255,136,0.6)]" : "bg-white/10"}`} />
                    ))}
                </div>

                <div className="h-[350px] w-full relative">
                    <AnimatePresence mode="wait" custom={1}>
                        {step === 1 && (
                            <motion.div key="step1" custom={1} variants={variants} initial="enter" animate="center" exit="exit" transition={{ type: "spring", stiffness: 300, damping: 30 }} className="flex flex-col items-center text-center absolute inset-0">
                                <div className="h-24 w-24 rounded-full bg-[#00ff88]/10 flex items-center justify-center mb-6 text-[#00ff88] border border-[#00ff88]/30 shadow-[0_0_30px_rgba(0,255,136,0.2)]">
                                    <Zap size={48} />
                                </div>
                                <h1 className="text-4xl font-extrabold font-mono tracking-tighter text-[#00ff88]">Welcome to CyberVPN</h1>
                                <p className="text-muted-foreground mt-4 text-lg">Next-generation privacy infrastructure engineered for extreme stealth, routing efficiency, and absolute zero-knowledge connectivity.</p>
                                <button onClick={() => setStep(2)} className="mt-10 px-8 py-3 bg-[#00ff88]/20 text-[#00ff88] rounded-full border border-[#00ff88]/40 font-bold tracking-widest hover:bg-[#00ff88] hover:text-black transition-all flex items-center gap-2">
                                    INITIALIZE NEURAL LINK <ArrowRight size={18} />
                                </button>
                            </motion.div>
                        )}

                        {step === 2 && (
                            <motion.div key="step2" custom={1} variants={variants} initial="enter" animate="center" exit="exit" transition={{ type: "spring", stiffness: 300, damping: 30 }} className="flex flex-col items-center text-center absolute inset-0">
                                <div className="h-24 w-24 rounded-full bg-yellow-500/10 flex items-center justify-center mb-6 text-yellow-500 border border-yellow-500/30 shadow-[0_0_30px_rgba(234,179,8,0.2)]">
                                    <Shield size={48} />
                                </div>
                                <h1 className="text-3xl font-extrabold font-mono tracking-tighter text-yellow-500">Root / Admin Privileges</h1>
                                <p className="text-muted-foreground mt-4 text-base px-6">CyberVPN employs advanced <span className="text-[#00ffff] font-mono">TUN Device Injection</span> to capture all OS layer packets before they hit your ISP. This guarantees 100% leak protection but requires administrative prompts upon your first connection.</p>
                                <div className="mt-6 flex flex-col gap-2 w-full max-w-sm text-left font-mono text-xs text-white/40 bg-black/40 p-3 rounded-lg border border-white/5">
                                    <div className="flex gap-2 items-center"><CheckCircle size={12} className="text-[#00ff88]" /> Bypasses DNS Leaks natively</div>
                                    <div className="flex gap-2 items-center"><CheckCircle size={12} className="text-[#00ff88]" /> Intercepts UDP protocols</div>
                                    <div className="flex gap-2 items-center"><CheckCircle size={12} className="text-[#00ff88]" /> Ensures process-level killswitches</div>
                                </div>
                                <button onClick={() => setStep(3)} className="mt-8 px-8 py-3 bg-white/5 text-white rounded-full border border-white/10 font-bold tracking-widest hover:bg-white hover:text-black transition-all flex items-center gap-2">
                                    I UNDERSTAND <ArrowRight size={18} />
                                </button>
                            </motion.div>
                        )}

                        {step === 3 && (
                            <motion.div key="step3" custom={1} variants={variants} initial="enter" animate="center" exit="exit" transition={{ type: "spring", stiffness: 300, damping: 30 }} className="flex flex-col items-center text-center absolute inset-0">
                                <div className="h-24 w-24 rounded-full bg-[#00ffff]/10 flex items-center justify-center mb-6 text-[#00ffff] border border-[#00ffff]/30 shadow-[0_0_30px_rgba(0,255,255,0.2)]">
                                    <Network size={48} />
                                </div>
                                <h1 className="text-3xl font-extrabold font-mono tracking-tighter text-[#00ffff]">System Ready</h1>
                                <p className="text-muted-foreground mt-4 text-base">Your environment is configured. You can now import a subscription node, or scan a remote QR code to sync directly with your devices.</p>
                                <button onClick={finishOnboarding} className="mt-10 px-10 py-4 bg-[#00ffff] text-black shadow-[0_0_40px_rgba(0,255,255,0.4)] rounded-full border border-[#00ffff] font-extrabold tracking-widest hover:bg-white transition-all flex items-center gap-2 scale-105">
                                    ENTER THE GRID
                                </button>
                                <div className="mt-6 text-xs text-white/30 font-mono flex items-center gap-2">
                                    <QrCode size={14} /> Import nodes inside the Main Dashboard
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>

            {/* Scanlines Effect */}
            <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(0,0,0,0)_50%,rgba(0,0,0,0.1)_50%)] bg-[length:100%_4px] mix-blend-overlay z-[100] opacity-10" />
        </div>
    );
}
