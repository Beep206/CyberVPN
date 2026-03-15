import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { RoutingRule, getRoutingRules, addRoutingRule, updateRoutingRule, deleteRoutingRule } from "../../shared/api/ipc";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Switch } from "../../components/ui/switch";
import { Label } from "../../components/ui/label";

export function RoutingPage() {
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
            toast.error("Failed to load routing rules");
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
            toast.error("Please provide at least one Domain or IP");
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
            toast.success("Rule added successfully");
            setDomains("");
            setIps("");
            setOutbound("proxy");
            setIsAdding(false);
            fetchRules();
        } catch (error: any) {
            toast.error(`Failed to add rule: ${error}`);
        }
    };

    const handleToggle = async (rule: RoutingRule) => {
        try {
            const updated = { ...rule, enabled: !rule.enabled };
            await updateRoutingRule(updated);
            fetchRules();
        } catch (e: any) {
            toast.error(`Failed to update rule`);
        }
    };

    const handleDelete = async (id: string) => {
        try {
            await deleteRoutingRule(id);
            toast.success("Rule deleted");
            fetchRules();
        } catch (e: any) {
            toast.error(`Failed to delete rule`);
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
                        <RouteIcon /> Routing Engine
                    </h1>
                    <p className="text-muted-foreground mt-2 text-sm tracking-wide">
                        Configure custom detours and DNS overrides. Rules are evaluated top to bottom.
                    </p>
                </div>
                <button 
                    onClick={() => setIsAdding(!isAdding)}
                    className="flex items-center gap-2 bg-[var(--color-neon-cyan)]/10 hover:bg-[var(--color-neon-cyan)]/20 text-[var(--color-neon-cyan)] border border-[var(--color-neon-cyan)]/50 px-4 py-2 rounded-md transition-all font-bold tracking-widest uppercase text-xs shadow-[0_0_15px_rgba(0,255,255,0.1)]"
                >
                    <Plus size={16} /> {isAdding ? "Cancel" : "Add Rule"}
                </button>
            </div>

            {isAdding && (
                <Card className="border-[var(--color-neon-cyan)]/30 bg-black/40 backdrop-blur shadow-[0_0_20px_rgba(0,255,255,0.05)]">
                    <CardHeader>
                        <CardTitle className="text-[var(--color-neon-cyan)] uppercase tracking-widest text-sm">New Route Directive</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleAdd} className="flex flex-col gap-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label className="text-muted-foreground uppercase text-xs tracking-wider">Domains (comma separated)</Label>
                                    <input 
                                        type="text" 
                                        value={domains}
                                        onChange={e => setDomains(e.target.value)}
                                        placeholder="e.g. *.openai.com, geosite:google" 
                                        className="flex h-10 w-full rounded-md border border-border/50 bg-background/50 px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--color-matrix-green)]"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-muted-foreground uppercase text-xs tracking-wider">IPs / CIDRs (comma separated)</Label>
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
                                <Label className="text-muted-foreground uppercase text-xs tracking-wider">Target Outbound</Label>
                                <select 
                                    value={outbound}
                                    onChange={e => setOutbound(e.target.value)}
                                    className="flex h-10 w-full rounded-md border border-border/50 bg-background/50 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--color-matrix-green)]"
                                >
                                    <option value="proxy">Proxy</option>
                                    <option value="direct">Direct (Bypass)</option>
                                    <option value="block">Block (Reject)</option>
                                </select>
                            </div>

                            <button type="submit" className="mt-2 bg-[var(--color-matrix-green)]/20 hover:bg-[var(--color-matrix-green)]/30 text-[var(--color-matrix-green)] border border-[var(--color-matrix-green)]/50 px-4 py-2 rounded-md transition-all font-bold tracking-widest uppercase text-xs w-fit">
                                Inject Rule
                            </button>
                        </form>
                    </CardContent>
                </Card>
            )}

            <div className="flex flex-col gap-3">
                {rules.length === 0 && !isAdding && (
                    <div className="text-center py-12 text-muted-foreground/50 border border-dashed border-border/30 rounded-xl bg-black/20">
                        No custom routing rules defined. All traffic flows through strictly default paths.
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
