import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Plus, Trash2, Code, PlaySquare, Hexagon } from "lucide-react";
import { toast } from "sonner";
import { RoutingRule, getRoutingRules, addRoutingRule, updateRoutingRule, deleteRoutingRule } from "../../shared/api/ipc";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Switch } from "../../components/ui/switch";
import { Label } from "../../components/ui/label";
import { useTranslation } from "react-i18next";

export function RoutingPage() {
    const { t } = useTranslation();
    const [rules, setRules] = useState<RoutingRule[]>([]);
    const [isAdding, setIsAdding] = useState(false);
    
    // Form state
    const [domains, setDomains] = useState("");
    const [ips, setIps] = useState("");
    const [outbound, setOutbound] = useState("proxy");

    const fetchRules = async () => {
        try {
            const data = await getRoutingRules();
            setRules(data);
        } catch (e: any) {
            toast.error(t('routingEngine.loadError'));
        }
    };

    useEffect(() => {
        fetchRules();
    }, []);

    const handleAdd = async (e: React.FormEvent) => {
        e.preventDefault();
        
        const domainList = domains.split(",").map(d => d.trim()).filter(d => d.length > 0);
        const ipList = ips.split(",").map(i => i.trim()).filter(i => i.length > 0);
        
        if (domainList.length === 0 && ipList.length === 0) {
            toast.error(t('routingEngine.atLeastOne'));
            return;
        }

        const newRule: RoutingRule = {
            id: crypto.randomUUID(),
            enabled: true,
            domains: domainList,
            ips: ipList,
            outbound,
        };

        try {
            await addRoutingRule(newRule);
            toast.success(t('routingEngine.ruleAdded'));
            setDomains("");
            setIps("");
            setOutbound("proxy");
            setIsAdding(false);
            fetchRules();
        } catch (error: any) {
            toast.error(t('routingEngine.addError', { error }));
        }
    };

    const handleToggle = async (rule: RoutingRule) => {
        try {
            const updated = { ...rule, enabled: !rule.enabled };
            await updateRoutingRule(updated);
            fetchRules();
        } catch (e: any) {
            toast.error(t('routingEngine.toggleError'));
        }
    };

    const handleDelete = async (id: string) => {
        try {
            await deleteRoutingRule(id);
            toast.success(t('routingEngine.ruleDeleted'));
            fetchRules();
        } catch (e: any) {
            toast.error(t('routingEngine.deleteError'));
        }
    };

    const applyPresetPack = async (packId: string) => {
        let presetDomains: string[] = [];
        let packName = "";

        if (packId === "social") {
             presetDomains = ["domain:twitter.com", "domain:x.com", "domain:facebook.com", "domain:instagram.com", "domain:chatgpt.com"];
             packName = t('routingEngine.socialPack');
        } else if (packId === "dev") {
             presetDomains = ["domain:github.com", "domain:docker.com", "domain:stackoverflow.com"];
             packName = t('routingEngine.devPack');
        } else if (packId === "stream") {
             presetDomains = ["domain:youtube.com", "domain:twitch.tv", "domain:netflix.com"];
             packName = t('routingEngine.streamerPack');
        }

        const newRule: RoutingRule = {
            id: crypto.randomUUID(),
            enabled: true,
            domains: presetDomains,
            ips: [],
            outbound: "proxy",
        };

        try {
            toast.loading(t('routingEngine.injecting', { pack: packName }), { id: "preset" });
            await addRoutingRule(newRule);
            toast.success(t('routingEngine.injected', { pack: packName }), { id: "preset" });
            fetchRules();
        } catch (error: any) {
            toast.error(t('routingEngine.injectionFailed', { error }), { id: "preset" });
        }
    };

    return (
        <motion.div 
            className="flex flex-col gap-6"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
        >
            <div className="flex justify-between items-end border-b border-border/50 pb-6">
                <div>
                    <h1 className="text-3xl font-bold tracking-wider text-[var(--color-matrix-green)] drop-shadow-[0_0_8px_rgba(0,255,136,0.6)] uppercase flex items-center gap-3">
                        <RouteIcon /> {t('routingEngine.title')}
                    </h1>
                    <p className="text-muted-foreground mt-2 text-sm tracking-wide">
                        {t('routingEngine.description')}
                    </p>
                </div>
                <button 
                    onClick={() => setIsAdding(!isAdding)}
                    className="flex items-center gap-2 bg-[var(--color-neon-cyan)]/10 hover:bg-[var(--color-neon-cyan)]/20 text-[var(--color-neon-cyan)] border border-[var(--color-neon-cyan)]/50 px-4 py-2 rounded-md transition-all font-bold tracking-widest uppercase text-xs shadow-[0_0_15px_rgba(0,255,255,0.1)]"
                >
                    <Plus size={16} /> {isAdding ? t('routingEngine.cancel') : t('routingEngine.addRule')}
                </button>
            </div>

            {isAdding && (
                <Card className="border-[var(--color-neon-cyan)]/30 bg-black/40 backdrop-blur shadow-[0_0_20px_rgba(0,255,255,0.05)]">
                    <CardHeader>
                        <CardTitle className="text-[var(--color-neon-cyan)] uppercase tracking-widest text-sm">{t('routingEngine.newRouteDirective')}</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleAdd} className="flex flex-col gap-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label className="text-muted-foreground uppercase text-xs tracking-wider">{t('routingEngine.domainsLabel')}</Label>
                                    <input 
                                        type="text" 
                                        value={domains}
                                        onChange={e => setDomains(e.target.value)}
                                        placeholder="e.g. *.openai.com, geosite:google" 
                                        className="flex h-10 w-full rounded-md border border-border/50 bg-background/50 px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--color-matrix-green)]"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-muted-foreground uppercase text-xs tracking-wider">{t('routingEngine.ipsLabel')}</Label>
                                    <input 
                                        type="text" 
                                        value={ips}
                                        onChange={e => setIps(e.target.value)}
                                        placeholder="e.g. 192.168.1.0/24, geoip:telegram" 
                                        className="flex h-10 w-full rounded-md border border-border/50 bg-background/50 px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--color-matrix-green)]"
                                    />
                                </div>
                            </div>
                            
                            <div className="space-y-2 w-1/3">
                                <Label className="text-muted-foreground uppercase text-xs tracking-wider">{t('routingEngine.targetOutbound')}</Label>
                                <select 
                                    value={outbound}
                                    onChange={e => setOutbound(e.target.value)}
                                    className="flex h-10 w-full rounded-md border border-border/50 bg-background/50 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--color-matrix-green)]"
                                >
                                    <option value="proxy">{t('routingEngine.outboundProxy')}</option>
                                    <option value="direct">{t('routingEngine.outboundDirect')}</option>
                                    <option value="block">{t('routingEngine.outboundBlock')}</option>
                                </select>
                            </div>

                            <button type="submit" className="mt-2 bg-[var(--color-matrix-green)]/20 hover:bg-[var(--color-matrix-green)]/30 text-[var(--color-matrix-green)] border border-[var(--color-matrix-green)]/50 px-4 py-2 rounded-md transition-all font-bold tracking-widest uppercase text-xs w-fit">
                                {t('routingEngine.injectRule')}
                            </button>
                        </form>
                    </CardContent>
                </Card>
            )}

            {!isAdding && rules.length === 0 && (
                <motion.div 
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-4"
                >
                    {/* Preset 1 */}
                    <motion.div 
                        whileHover={{ scale: 1.02, textShadow: "0 0 8px rgba(0,255,255,0.8)" }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => applyPresetPack("social")}
                        className="p-5 flex flex-col items-center justify-center text-center gap-3 rounded-2xl border border-[var(--color-neon-cyan)]/30 bg-black/40 cursor-pointer shadow-[0_0_15px_rgba(0,255,255,0.05)] hover:border-[var(--color-neon-cyan)] hover:shadow-[0_0_20px_rgba(0,255,255,0.2)] transition-all"
                    >
                         <Hexagon size={28} className="text-[var(--color-neon-cyan)]" />
                     <div>
                            <h3 className="font-bold tracking-widest text-sm text-[var(--color-neon-cyan)] uppercase">{t('routingEngine.socialPack')}</h3>
                            <p className="text-[10px] text-muted-foreground uppercase tracking-widest mt-1">X, Meta, ChatGPT</p>
                         </div>
                    </motion.div>

                    {/* Preset 2 */}
                    <motion.div 
                        whileHover={{ scale: 1.02, textShadow: "0 0 8px rgba(0,255,136,0.8)" }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => applyPresetPack("dev")}
                        className="p-5 flex flex-col items-center justify-center text-center gap-3 rounded-2xl border border-[var(--color-matrix-green)]/30 bg-black/40 cursor-pointer shadow-[0_0_15px_rgba(0,255,136,0.05)] hover:border-[var(--color-matrix-green)] hover:shadow-[0_0_20px_rgba(0,255,136,0.2)] transition-all"
                    >
                         <Code size={28} className="text-[var(--color-matrix-green)]" />
                         <div>
                            <h3 className="font-bold tracking-widest text-sm text-[var(--color-matrix-green)] uppercase">{t('routingEngine.devPack')}</h3>
                            <p className="text-[10px] text-muted-foreground uppercase tracking-widest mt-1">GitHub, Docker</p>
                         </div>
                    </motion.div>

                     {/* Preset 3 */}
                     <motion.div 
                        whileHover={{ scale: 1.02, textShadow: "0 0 8px rgba(255,0,255,0.8)" }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => applyPresetPack("stream")}
                        className="p-5 flex flex-col items-center justify-center text-center gap-3 rounded-2xl border border-[var(--color-neon-pink)]/30 bg-black/40 cursor-pointer shadow-[0_0_15px_rgba(255,0,255,0.05)] hover:border-[var(--color-neon-pink)] hover:shadow-[0_0_20px_rgba(255,0,255,0.2)] transition-all"
                    >
                         <PlaySquare size={28} className="text-[var(--color-neon-pink)]" />
                         <div>
                            <h3 className="font-bold tracking-widest text-sm text-[var(--color-neon-pink)] uppercase">{t('routingEngine.streamerPack')}</h3>
                            <p className="text-[10px] text-muted-foreground uppercase tracking-widest mt-1">Youtube, Twitch</p>
                         </div>
                    </motion.div>
                </motion.div>
            )}

            <div className="flex flex-col gap-3">
                {rules.length === 0 && !isAdding && (
                    <div className="text-center py-12 text-muted-foreground/50 border border-dashed border-border/30 rounded-xl bg-black/20">
                        {t('routingEngine.noRules')}
                    </div>
                )}
                
                {rules.map((rule) => (
                    <div 
                        key={rule.id} 
                        className={`flex items-center justify-between p-4 rounded-xl border backdrop-blur transition-all ${rule.enabled ? 'bg-black/40 border-[var(--color-matrix-green)]/20' : 'bg-black/20 border-border/30 opacity-70'}`}
                    >
                        <div className="flex items-center gap-6">
                            <div className="flex flex-col items-center gap-1 min-w-[60px]">
                                <Switch checked={rule.enabled} onCheckedChange={() => handleToggle(rule)} />
                            </div>
                            
                            <div className="flex flex-col gap-1">
                                <div className="flex items-center gap-2">
                                    <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider ${
                                        rule.outbound === "proxy" ? "bg-[var(--color-neon-cyan)]/20 text-[var(--color-neon-cyan)] border border-[var(--color-neon-cyan)]/30" : 
                                        rule.outbound === "direct" ? "bg-[var(--color-matrix-green)]/20 text-[var(--color-matrix-green)] border border-[var(--color-matrix-green)]/30" : 
                                        "bg-[var(--color-neon-pink)]/20 text-[var(--color-neon-pink)] border border-[var(--color-neon-pink)]/30"
                                    }`}>
                                        {rule.outbound}
                                    </span>
                                    {rule.domains.length > 0 && <span className="text-xs font-mono text-muted-foreground">{rule.domains.join(", ")}</span>}
                                </div>
                                {rule.ips.length > 0 && (
                                    <span className="text-xs font-mono text-muted-foreground/70">{rule.ips.join(", ")}</span>
                                )}
                            </div>
                        </div>

                        <button 
                            onClick={() => handleDelete(rule.id)}
                            className="p-2 text-muted-foreground hover:text-[var(--color-neon-pink)] transition-colors"
                        >
                            <Trash2 size={18} />
                        </button>
                    </div>
                ))}
            </div>
        </motion.div>
    );
}

function RouteIcon() {
    return (
        <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/>
        </svg>
    )
}
