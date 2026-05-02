import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Shield, Plus, Trash2, Server, Globe, Key, ClipboardPaste, ScanLine, Share2 } from "lucide-react";
import { getProfiles, addProfile, parseClipboardLink, scanScreenForQr, generateLink, ProxyNode } from "../../shared/api/ipc";
import { QRCodeSVG } from "qrcode.react";
import { toast } from "sonner";
import { CyberButton } from "../../shared/ui/atoms/cyber-button";
import { GlassCard } from "../../shared/ui/atoms/glass-card";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
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

export function ProfilesPage() {
  const { t } = useTranslation();
  const { prefersReducedMotion, durations, offsets } = useDesktopMotionBudget();
  const [profiles, setProfiles] = useState<ProxyNode[]>([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isShareOpen, setIsShareOpen] = useState(false);
  const [shareLink, setShareLink] = useState("");
  const [shareNodeName, setShareNodeName] = useState("");
  const [isScanning, setIsScanning] = useState(false);

  // Form state
  const [name, setName] = useState("");
  const [server, setServer] = useState("");
  const [port, setPort] = useState("443");
  const [protocol, setProtocol] = useState("vless");
  const [uuid, setUuid] = useState("");
  const [nextHopId, setNextHopId] = useState<string>("");
  const nextHopSelectValue = nextHopId || "__direct__";

  const refreshProfiles = async () => {
    try {
      const data = await getProfiles();
      setProfiles(data);
    } catch (e) {
      console.error("Failed to load profiles", e);
    }
  };

  useEffect(() => {
    refreshProfiles();
  }, []);

  const isLikelySubscriptionUrl = (value: string) => {
    try {
      const parsed = new URL(value.trim());
      const isHttp = parsed.protocol === "http:" || parsed.protocol === "https:";
      const hasBasicAuth = Boolean(parsed.username) || Boolean(parsed.password);
      const hasNonRootPath = parsed.pathname !== "/" && parsed.pathname !== "";
      const hasQuery = Boolean(parsed.search);
      const hasSubscriptionLikePath = /sub|subscribe|subscription|clash|sing[-_]?box/i.test(
        parsed.pathname
      );

      return isHttp && !hasBasicAuth && (hasSubscriptionLikePath || hasQuery || hasNonRootPath);
    } catch {
      return false;
    }
  };

  const handleCreateProfile = async () => {
    const newProfile: ProxyNode = {
      id: crypto.randomUUID(),
      name,
      server,
      port: parseInt(port, 10),
      protocol,
      uuid,
      nextHopId: nextHopId || undefined,
    };

    try {
      await addProfile(newProfile);
      setIsDialogOpen(false);
      
      // reset form
      setName("");
      setServer("");
      setUuid("");
      
      refreshProfiles();
      toast.success(t('profiles.createSuccess'));
    } catch (e: any) {
      console.error("Failed to create profile", e);
      toast.error(t('profiles.createError', { error: e }));
    }
  };

  const handlePasteFromClipboard = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (!text) {
        toast.error(t('profiles.clipboardEmpty'));
        return;
      }

      if (isLikelySubscriptionUrl(text)) {
        toast.error(
          t('profiles.subscriptionUrlHint', {
            destination: t('subscriptions.title'),
          })
        );
        return;
      }
      
      const parsedNode = await parseClipboardLink(text);
      await addProfile(parsedNode);
      await refreshProfiles();
      toast.success(t('profiles.importSuccess', { name: parsedNode.name }));
    } catch (e: any) {
      toast.error(t('profiles.importError', { error: e }));
    }
  };

  const handleScanScreen = async () => {
    setIsScanning(true);
    try {
      toast.info(t('profiles.scanning'));
      const parsedNode = await scanScreenForQr();
      await addProfile(parsedNode);
      await refreshProfiles();
      toast.success(t('profiles.scanSuccess', { name: parsedNode.name }));
    } catch (e: any) {
      console.error(e);
      toast.error(t('profiles.scanError', { error: e }));
    } finally {
      setIsScanning(false);
    }
  };

  const handleShare = async (node: ProxyNode) => {
    try {
      const link = await generateLink(node);
      setShareLink(link);
      setShareNodeName(node.name);
      setIsShareOpen(true);
    } catch (e: any) {
      toast.error(t('profiles.shareFailed', { error: e }));
    }
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
               {t('profiles.title')}
           </h1>
           <p className="text-muted-foreground mt-2">{t('profiles.description')}</p>
        </div>
        
        <div className="flex gap-3">
          <CyberButton variant="secondary" onClick={handleScanScreen} disabled={isScanning} className="gap-2 border-[var(--color-neon-cyan)]/30 text-[var(--color-neon-cyan)]">
            <ScanLine size={16} className={isScanning ? "animate-spin" : ""} />
            {t('profiles.scanQr')}
          </CyberButton>
          
          <CyberButton variant="secondary" onClick={handlePasteFromClipboard} className="gap-2 border-border/60 hover:bg-accent/70">
            <ClipboardPaste size={16} />
            {t('profiles.paste')}
          </CyberButton>

          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger
              render={
                <CyberButton variant="primary" className="gap-2" />
              }
            >
              <Plus size={16} />
              {t('profiles.addNode')}
            </DialogTrigger>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle className="text-[var(--color-matrix-green)] tracking-wide">{t('profiles.addDialogTitle')}</DialogTitle>
              <DialogDescription>
                {t('profiles.addDialogDesc')}
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="name" className="text-right">{t('profiles.name')}</Label>
                <Input id="name" value={name} onChange={e => setName(e.target.value)} className="col-span-3" placeholder={t('profiles.namePlaceholder')} />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="server" className="text-right">{t('profiles.serverIp')}</Label>
                <Input id="server" value={server} onChange={e => setServer(e.target.value)} className="col-span-3" placeholder={t('profiles.serverPlaceholder')} />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="port" className="text-right">{t('profiles.port')}</Label>
                <Input id="port" value={port} onChange={e => setPort(e.target.value)} className="col-span-3" type="number" />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="protocol" className="text-right">{t('profiles.protocol')}</Label>
                <Input id="protocol" value={protocol} onChange={e => setProtocol(e.target.value)} className="col-span-3" placeholder="vless" />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="uuid" className="text-right">{t('profiles.uuid')}</Label>
                <Input id="uuid" value={uuid} onChange={e => setUuid(e.target.value)} className="col-span-3" type="password" />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="nextHop" className="text-right">{t('profiles.nextHop')}</Label>
                <Select
                  value={nextHopSelectValue}
                  onValueChange={(value) => setNextHopId(value === "__direct__" ? "" : String(value))}
                >
                  <SelectTrigger id="nextHop" className="col-span-3 w-full">
                    <SelectValue>
                      {(value) => {
                        if (value === "__direct__" || !value) {
                          return t('profiles.noneDirect');
                        }

                        const selectedProfile = profiles.find((profile) => profile.id === value);
                        return selectedProfile
                          ? `${selectedProfile.name} (${selectedProfile.server})`
                          : t('profiles.unknown');
                      }}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent align="start">
                    <SelectItem value="__direct__">{t('profiles.noneDirect')}</SelectItem>
                    {profiles.map((profile) => (
                      <SelectItem key={profile.id} value={profile.id}>
                        {profile.name} ({profile.server})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <CyberButton onClick={handleCreateProfile} variant="primary">{t('profiles.saveProfile')}</CyberButton>
            </DialogFooter>
          </DialogContent>
          </Dialog>
        </div>
      </header>

      <Dialog open={isShareOpen} onOpenChange={setIsShareOpen}>
        <DialogContent className="flex flex-col items-center pt-8 pb-8 sm:max-w-[400px]">
            <DialogHeader className="w-full text-center mb-4">
              <DialogTitle className="text-[var(--color-neon-cyan)] tracking-wide">{t('profiles.shareNode')}</DialogTitle>
              <DialogDescription>{shareNodeName}</DialogDescription>
            </DialogHeader>
            <div className="rounded-2xl border border-border/70 bg-[color:var(--panel-subtle)] p-4 shadow-[0_0_20px_rgba(0,255,255,0.12)]">
                <div className="rounded-xl bg-white p-3">
                    <QRCodeSVG value={shareLink} size={256} className="pointer-events-none" />
                </div>
            </div>
            <div className="flex flex-col items-center mt-6 w-full px-4 text-center">
                <p className="w-full break-all rounded-lg border border-border/50 bg-[color:var(--panel-subtle)] p-3 font-mono text-xs text-muted-foreground/80 select-all">
                    {shareLink}
                </p>
                <CyberButton
                    variant="secondary"
                    className="w-full mt-4 border-[var(--color-neon-cyan)]/50 text-[var(--color-neon-cyan)]"
                    onClick={() => {
                        navigator.clipboard.writeText(shareLink);
                        toast.success(t('profiles.copied'));
                    }}
                >
                    <ClipboardPaste size={16} className="mr-2" />
                    {t('profiles.copyRawLink')}
                </CyberButton>
            </div>
        </DialogContent>
      </Dialog>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pb-8">
         <AnimatePresence initial={false}>
             {profiles.map((p) => (
                 <GlassCard
                     key={p.id}
                     variant="stealth"
                     withScanlines
                     className="group relative flex flex-col hover:border-[var(--color-neon-cyan)]/50 transition-all duration-300"
                 >
                     <div className="flex justify-between items-start mb-4">
                         <div className="flex items-center gap-3">
                             <div className="p-2 rounded-md bg-[var(--color-neon-cyan)]/10 text-[var(--color-neon-cyan)] group-hover:bg-[var(--color-neon-cyan)]/20 transition-colors">
                                 <Shield size={20} />
                             </div>
                             <h3 className="font-semibold text-lg hover:text-[var(--color-neon-cyan)] transition-colors">{p.name}</h3>
                         </div>
                         <div className="flex gap-2">
                             <button onClick={() => handleShare(p)} className="p-2 -mr-2 text-muted-foreground hover:text-[var(--color-neon-cyan)] opacity-0 group-hover:opacity-100 transition-opacity">
                                 <Share2 size={16} />
                             </button>
                             <button className="p-2 -mr-2 text-muted-foreground hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity">
                                 <Trash2 size={16} />
                             </button>
                         </div>
                     </div>
                     
                     <div className="space-y-2 text-sm text-muted-foreground/80 font-mono">
                         <div className="flex items-center gap-2">
                             <Server size={14} className="text-[var(--color-neon-cyan)]" />
                             <span className="truncate">{p.server}:{p.port}</span>
                         </div>
                         <div className="flex items-center gap-2">
                             <Globe size={14} className="text-[var(--color-neon-pink)]" />
                             <span className="uppercase">{p.protocol}</span>
                         </div>
                         {p.uuid && (
                             <div className="flex items-center gap-2">
                                 <Key size={14} className="opacity-60" />
                                 <span className="truncate text-xs opacity-60">{p.uuid.substring(0, 8)}...</span>
                             </div>
                         )}
                         {p.nextHopId && (
                             <div className="flex items-center gap-2 mt-2 pt-2 border-t border-border/30">
                                 <Globe size={14} className="text-[var(--color-matrix-green)]" />
                                 <span className="text-xs text-[var(--color-matrix-green)]">{t('profiles.chain')} → {profiles.find(x => x.id === p.nextHopId)?.name || t('profiles.unknown')}</span>
                             </div>
                         )}
                     </div>
                 </GlassCard>
             ))}
         </AnimatePresence>
         
         {profiles.length === 0 && (
             <div className="col-span-full py-16 flex flex-col items-center justify-center text-muted-foreground/50 border border-dashed border-border/60 rounded-xl">
                 <Shield className="w-12 h-12 mb-4 opacity-20" />
                 <p className="font-mono text-sm">{t('profiles.noProfiles')}</p>
             </div>
         )}
      </div>
    </motion.div>
  );
}
