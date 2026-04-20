import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Rss, Plus, RefreshCw, Layers, Shield, Monitor, ShoppingCart } from "lucide-react";
import {
  addSubscription,
  CanonicalCurrentServiceState,
  CanonicalEntitlementState,
  CanonicalOrder,
  getCanonicalCurrentEntitlements,
  getCanonicalCurrentServiceState,
  getCanonicalOrders,
  getProfiles,
  getSubscriptions,
  ProxyNode,
  Subscription,
  updateSubscription,
} from "../../shared/api/ipc";
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
import { desktopMotionEase, useDesktopMotionBudget } from "../../shared/lib/motion";
import { useTranslation } from "react-i18next";

export function SubscriptionsPage() {
  const { t } = useTranslation();
  const { prefersReducedMotion, durations, offsets } = useDesktopMotionBudget();
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [profiles, setProfiles] = useState<ProxyNode[]>([]);
  const [canonicalEntitlement, setCanonicalEntitlement] =
    useState<CanonicalEntitlementState | null>(null);
  const [canonicalServiceState, setCanonicalServiceState] =
    useState<CanonicalCurrentServiceState | null>(null);
  const [canonicalOrders, setCanonicalOrders] = useState<CanonicalOrder[]>([]);
  const [canonicalUnavailable, setCanonicalUnavailable] = useState(false);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isSyncing, setIsSyncing] = useState<Record<string, boolean>>({});

  // Form state
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");

  const formatCanonicalDate = (value?: string | null) => {
    if (!value) return "Not available";
    return new Date(value).toLocaleString();
  };

  const formatMoney = (amount: number, currencyCode = "USD") => {
    try {
      return new Intl.NumberFormat(undefined, {
        style: "currency",
        currency: currencyCode,
        maximumFractionDigits: 2,
      }).format(amount);
    } catch {
      return `${amount.toFixed(2)} ${currencyCode}`;
    }
  };

  const refreshData = async () => {
    try {
      const [subsData, profilesData] = await Promise.all([getSubscriptions(), getProfiles()]);
      setSubscriptions(subsData);
      setProfiles(profilesData);

      const [entitlementResult, serviceStateResult, ordersResult] =
        await Promise.allSettled([
          getCanonicalCurrentEntitlements(),
          getCanonicalCurrentServiceState(),
          getCanonicalOrders(5),
        ]);

      setCanonicalUnavailable(false);

      if (entitlementResult.status === "fulfilled") {
        setCanonicalEntitlement(entitlementResult.value);
      } else {
        setCanonicalEntitlement(null);
        setCanonicalUnavailable(true);
      }

      if (serviceStateResult.status === "fulfilled") {
        setCanonicalServiceState(serviceStateResult.value);
      } else {
        setCanonicalServiceState(null);
        setCanonicalUnavailable(true);
      }

      if (ordersResult.status === "fulfilled") {
        setCanonicalOrders(ordersResult.value);
      } else {
        setCanonicalOrders([]);
        setCanonicalUnavailable(true);
      }
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
      initial={{ opacity: 0, y: offsets.page }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: prefersReducedMotion ? 0 : -4 }}
      transition={{ duration: durations.page, ease: desktopMotionEase }}
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
          <DialogTrigger
            render={
              <Button className="gap-2 bg-[var(--color-matrix-green)] text-black hover:bg-[var(--color-matrix-green)]/80 hover:shadow-[0_0_15px_rgba(0,255,136,0.6)] transition-all" />
            }
          >
            <Plus size={16} />
            {t('subscriptions.addUrl')}
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle className="text-[var(--color-matrix-green)] tracking-wide">{t('subscriptions.addSubscription')}</DialogTitle>
              <DialogDescription>
                {t('subscriptions.addDesc')}
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="name" className="text-right">{t('subscriptions.name')}</Label>
                <Input id="name" value={name} onChange={e => setName(e.target.value)} className="col-span-3" placeholder={t('subscriptions.namePlaceholder')} />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="url" className="text-right">{t('subscriptions.urlLabel')}</Label>
                <Input id="url" value={url} onChange={e => setUrl(e.target.value)} className="col-span-3" placeholder="https://..." />
              </div>
            </div>
            <DialogFooter>
              <Button onClick={handleCreateSubscription} className="bg-[var(--color-neon-cyan)] text-black hover:bg-[var(--color-neon-cyan)]/80">{t('subscriptions.saveSync')}</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="rounded-xl border border-[var(--color-neon-cyan)]/25 bg-[color:var(--panel-subtle)] p-5">
          <div className="flex items-center gap-3 mb-4">
            <Shield size={18} className="text-[var(--color-neon-cyan)]" />
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-[0.24em] text-[var(--color-neon-cyan)]">
                Canonical Entitlement
              </h2>
              <p className="text-xs text-muted-foreground">
                Backend-owned subscription truth for desktop parity.
              </p>
            </div>
          </div>
          {canonicalEntitlement ? (
            <div className="space-y-3 text-sm">
              <div className="flex items-center justify-between gap-3">
                <span className="text-muted-foreground">Plan</span>
                <span className="font-semibold text-right">
                  {canonicalEntitlement.display_name ??
                    canonicalEntitlement.plan_code ??
                    canonicalEntitlement.plan_uuid ??
                    "Unassigned"}
                </span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-muted-foreground">Status</span>
                <span className="font-mono uppercase text-[var(--color-matrix-green)]">
                  {canonicalEntitlement.status}
                </span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-muted-foreground">Expires</span>
                <span className="text-right">
                  {formatCanonicalDate(canonicalEntitlement.expires_at)}
                </span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-muted-foreground">Trial</span>
                <span>{canonicalEntitlement.is_trial ? "Yes" : "No"}</span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Canonical entitlement snapshot is not available yet.
            </p>
          )}
        </div>

        <div className="rounded-xl border border-[var(--color-matrix-green)]/25 bg-[color:var(--panel-subtle)] p-5">
          <div className="flex items-center gap-3 mb-4">
            <Monitor size={18} className="text-[var(--color-matrix-green)]" />
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-[0.24em] text-[var(--color-matrix-green)]">
                Service Access
              </h2>
              <p className="text-xs text-muted-foreground">
                Desktop manifest delivery and provisioning state.
              </p>
            </div>
          </div>
          {canonicalServiceState ? (
            <div className="space-y-3 text-sm">
              <div className="flex items-center justify-between gap-3">
                <span className="text-muted-foreground">Provider</span>
                <span className="font-semibold">{canonicalServiceState.provider_name}</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-muted-foreground">Channel</span>
                <span className="text-right">
                  {canonicalServiceState.access_delivery_channel?.channel_type ??
                    canonicalServiceState.consumption_context.channel_type ??
                    "Not resolved"}
                </span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-muted-foreground">Profile</span>
                <span className="text-right">
                  {canonicalServiceState.provisioning_profile?.profile_key ??
                    canonicalServiceState.consumption_context.provisioning_profile_key ??
                    "Pending"}
                </span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-muted-foreground">Source</span>
                <span className="text-right">
                  {canonicalServiceState.purchase_context.source_type ?? "Unspecified"}
                </span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Canonical service-state snapshot is not available yet.
            </p>
          )}
        </div>

        <div className="rounded-xl border border-[var(--color-neon-pink)]/25 bg-[color:var(--panel-subtle)] p-5">
          <div className="flex items-center gap-3 mb-4">
            <ShoppingCart size={18} className="text-[var(--color-neon-pink)]" />
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-[0.24em] text-[var(--color-neon-pink)]">
                Recent Orders
              </h2>
              <p className="text-xs text-muted-foreground">
                Canonical commerce lineage available to desktop.
              </p>
            </div>
          </div>
          {canonicalOrders.length > 0 ? (
            <div className="space-y-3">
              {canonicalOrders.slice(0, 3).map((order) => (
                <div
                  key={order.id}
                  className="rounded-lg border border-border/40 bg-[color:var(--panel-surface)] px-3 py-2 text-sm"
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-medium">
                      {order.items[0]?.display_name ?? order.sale_channel}
                    </span>
                    <span className="font-mono text-xs uppercase text-[var(--color-matrix-green)]">
                      {order.settlement_status}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center justify-between gap-3 text-xs text-muted-foreground">
                    <span>{formatCanonicalDate(order.created_at)}</span>
                    <span>{formatMoney(order.displayed_price, order.currency_code)}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No canonical orders available for this desktop session yet.
            </p>
          )}
        </div>
      </div>

      {canonicalUnavailable && (
        <div className="rounded-lg border border-dashed border-[var(--color-neon-cyan)]/25 px-4 py-3 text-sm text-muted-foreground">
          Canonical desktop parity data is unavailable until this client has a live backend session
          and resolved manifest context.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pb-8">
         <AnimatePresence initial={false}>
             {subscriptions.map((sub) => {
                 const nodeCount = profiles.filter(p => p.subscriptionId === sub.id).length;
                 const syncing = isSyncing[sub.id];

                 return (
                 <motion.div
                     key={sub.id}
                     layout
                     initial={{ opacity: 0, y: offsets.list }}
                     animate={{ opacity: 1, y: 0 }}
                     exit={{ opacity: 0, y: prefersReducedMotion ? 0 : -4 }}
                     transition={{ duration: durations.list, ease: desktopMotionEase }}
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
