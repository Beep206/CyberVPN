import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Rss, Plus, RefreshCw, Layers } from "lucide-react";
import { getSubscriptions, addSubscription, updateSubscription, getProfiles, Subscription, ProxyNode } from "../../shared/api/ipc";
import { toast } from "sonner";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../../components/ui/dialog";
import { useTranslation } from "react-i18next";

export function SubscriptionsPage() {
  const { t } = useTranslation();
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [profiles, setProfiles] = useState<ProxyNode[]>([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isSyncing, setIsSyncing] = useState<Record<string, boolean>>({});

  // Form state
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");

  const refreshData = async () => {
    try {
      const [subsData, profilesData] = await Promise.all([
        getSubscriptions(),
        getProfiles()
      ]);
      setSubscriptions(subsData);
      setProfiles(profilesData);
    } catch (e) {
      console.error("Failed to load data", e);
    }
  };

  useEffect(() => {
    refreshData();
  }, []);

  const handleCreateSubscription = async () => {
    if (!name || !url) {
        toast.error(t('subscriptions.fillAllFields'));
        return;
    }
    
    const newSubscription: Subscription = {
      id: crypto.randomUUID(),
      name,
      url,
      autoUpdate: true,
    };

    try {
      await addSubscription(newSubscription);
      setIsDialogOpen(false);
      setName("");
      setUrl("");
      
      await handleSync(newSubscription.id);
    } catch (e: any) {
      console.error("Failed to create subscription", e);
      toast.error(t('subscriptions.createError', { error: e }));
    }
  };

  const handleSync = async (subId: string) => {
    setIsSyncing(prev => ({ ...prev, [subId]: true }));
    try {
        await updateSubscription(subId);
        toast.success(t('subscriptions.syncSuccess'));
        await refreshData();
    } catch (e: any) {
        toast.error(t('subscriptions.syncError', { error: e }));
    } finally {
        setIsSyncing(prev => ({ ...prev, [subId]: false }));
    }
  };

  const formatDate = (timestamp?: number) => {
      if (!timestamp) return t('subscriptions.neverUpdated');
      return new Date(timestamp * 1000).toLocaleString();
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 1.05 }}
      transition={{ duration: 0.2 }}
      className="flex flex-col h-full gap-8"
    >
      <header className="flex items-center justify-between">
        <div>
           <h1 className="text-3xl font-bold tracking-tight text-[var(--color-neon-cyan)] drop-shadow-[0_0_8px_rgba(0,255,255,0.4)]">
               {t('subscriptions.title')}
           </h1>
           <p className="text-muted-foreground mt-2">{t('subscriptions.description')}</p>
        </div>
        
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger>
            <Button className="gap-2 bg-[var(--color-matrix-green)] text-black hover:bg-[var(--color-matrix-green)]/80 hover:shadow-[0_0_15px_rgba(0,255,136,0.6)] transition-all">
              <Plus size={16} />
              {t('subscriptions.addUrl')}
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px] border-[var(--color-matrix-green)]/30 bg-card/95 backdrop-blur shadow-2xl">
            <DialogHeader>
              <DialogTitle className="text-[var(--color-matrix-green)] tracking-wide">{t('subscriptions.addSubscription')}</DialogTitle>
              <DialogDescription>
                {t('subscriptions.addDesc')}
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="name" className="text-right">{t('subscriptions.name')}</Label>
                <Input id="name" value={name} onChange={e => setName(e.target.value)} className="col-span-3 bg-black/40 border-border/50" placeholder={t('subscriptions.namePlaceholder')} />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="url" className="text-right">{t('subscriptions.urlLabel')}</Label>
                <Input id="url" value={url} onChange={e => setUrl(e.target.value)} className="col-span-3 bg-black/40 border-border/50" placeholder="https://..." />
              </div>
            </div>
            <DialogFooter>
              <Button onClick={handleCreateSubscription} className="bg-[var(--color-neon-cyan)] text-black hover:bg-[var(--color-neon-cyan)]/80">{t('subscriptions.saveSync')}</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pb-8">
         <AnimatePresence>
             {subscriptions.map((sub) => {
                 const nodeCount = profiles.filter(p => p.subscriptionId === sub.id).length;
                 const syncing = isSyncing[sub.id];

                 return (
                 <motion.div
                     key={sub.id}
                     layout
                     initial={{ opacity: 0, y: 20 }}
                     animate={{ opacity: 1, y: 0 }}
                     className="group relative flex flex-col p-5 rounded-xl border border-border/40 bg-card/10 hover:bg-card/30 hover:border-[var(--color-neon-cyan)]/50 transition-all duration-300"
                 >
                     <div className="flex justify-between items-start mb-4">
                         <div className="flex items-center gap-3">
                             <div className="p-2 rounded-md bg-[var(--color-neon-cyan)]/10 text-[var(--color-neon-cyan)] group-hover:bg-[var(--color-neon-cyan)]/20 transition-colors">
                                 <Rss size={20} />
                             </div>
                             <h3 className="font-semibold text-lg max-w-[150px] truncate">{sub.name}</h3>
                         </div>
                         <Button 
                             disabled={syncing}
                             variant="ghost" 
                             onClick={() => handleSync(sub.id)}
                             size="icon" 
                             className="text-[var(--color-matrix-green)] opacity-50 hover:opacity-100 transition-opacity"
                         >
                             <RefreshCw size={16} className={syncing ? "animate-spin" : ""} />
                         </Button>
                     </div>
                     
                     <div className="space-y-3 text-sm text-muted-foreground/80 font-mono">
                         <div className="flex items-center gap-2">
                             <Layers size={14} className="text-muted-foreground" />
                             <span>{t('subscriptions.nodesSynced', { count: nodeCount })}</span>
                         </div>
                         <div className="flex flex-col gap-1 text-xs opacity-70 border-t border-border/30 pt-3 mt-1">
                             <span className="truncate">{sub.url}</span>
                             <span>{t('subscriptions.lastSync')}: {formatDate(sub.lastUpdated)}</span>
                         </div>
                     </div>
                 </motion.div>
             )})}
         </AnimatePresence>
         
         {subscriptions.length === 0 && (
             <div className="col-span-full py-16 flex flex-col items-center justify-center text-muted-foreground/50 border border-dashed border-border/60 rounded-xl">
                 <Rss className="w-12 h-12 mb-4 opacity-20" />
                 <p className="font-mono text-sm">{t('subscriptions.empty')}</p>
             </div>
         )}
      </div>
    </motion.div>
  );
}
