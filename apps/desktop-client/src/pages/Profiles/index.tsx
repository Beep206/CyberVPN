import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Shield, Plus, Trash2, Server, Globe, Key, ClipboardPaste } from "lucide-react";
import { getProfiles, addProfile, parseClipboardLink, ProxyNode } from "../../shared/api/ipc";
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

export function ProfilesPage() {
  const [profiles, setProfiles] = useState<ProxyNode[]>([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  // Form state
  const [name, setName] = useState("");
  const [server, setServer] = useState("");
  const [port, setPort] = useState("443");
  const [protocol, setProtocol] = useState("vless");
  const [uuid, setUuid] = useState("");

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

  const handleCreateProfile = async () => {
    const newProfile: ProxyNode = {
      id: crypto.randomUUID(),
      name,
      server,
      port: parseInt(port, 10),
      protocol,
      uuid,
    };

    try {
      await addProfile(newProfile);
      setIsDialogOpen(false);
      
      // reset form
      setName("");
      setServer("");
      setUuid("");
      
      refreshProfiles();
      toast.success("Profile created successfully!");
    } catch (e: any) {
      console.error("Failed to create profile", e);
      toast.error(`Error: ${e}`);
    }
  };

  const handlePasteFromClipboard = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (!text) {
        toast.error("Clipboard is empty.");
        return;
      }
      
      const parsedNode = await parseClipboardLink(text);
      await addProfile(parsedNode);
      await refreshProfiles();
      toast.success(`Imported profile: ${parsedNode.name}`);
    } catch (e: any) {
      toast.error(`Failed to parse link: ${e}`);
    }
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
               Profiles
           </h1>
           <p className="text-muted-foreground mt-2">Manage your VPN and Proxy node configurations.</p>
        </div>
        
        <div className="flex gap-3">
          <Button variant="outline" onClick={handlePasteFromClipboard} className="gap-2 border-border/50 bg-black/40 hover:bg-black/60 transition-all">
            <ClipboardPaste size={16} />
            Paste from Clipboard
          </Button>

          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger>
              <Button className="gap-2 bg-[var(--color-matrix-green)] text-black hover:bg-[var(--color-matrix-green)]/80 hover:shadow-[0_0_15px_rgba(0,255,136,0.6)] transition-all">
                <Plus size={16} />
                Add Node
              </Button>
            </DialogTrigger>
          <DialogContent className="sm:max-w-[425px] border-[var(--color-matrix-green)]/30 bg-card/95 backdrop-blur shadow-2xl">
            <DialogHeader>
              <DialogTitle className="text-[var(--color-matrix-green)] tracking-wide">Add Proxy Node</DialogTitle>
              <DialogDescription>
                Enter the connection details for your new secure tunnel.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="name" className="text-right">Name</Label>
                <Input id="name" value={name} onChange={e => setName(e.target.value)} className="col-span-3 bg-black/40 border-border/50" placeholder="e.g. Frankfurt VLESS" />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="server" className="text-right">Server IP</Label>
                <Input id="server" value={server} onChange={e => setServer(e.target.value)} className="col-span-3 bg-black/40 border-border/50" placeholder="192.168.1.1" />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="port" className="text-right">Port</Label>
                <Input id="port" value={port} onChange={e => setPort(e.target.value)} className="col-span-3 bg-black/40 border-border/50" type="number" />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="protocol" className="text-right">Protocol</Label>
                <Input id="protocol" value={protocol} onChange={e => setProtocol(e.target.value)} className="col-span-3 bg-black/40 border-border/50" placeholder="vless" />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="uuid" className="text-right">UUID</Label>
                <Input id="uuid" value={uuid} onChange={e => setUuid(e.target.value)} className="col-span-3 bg-black/40 border-border/50" type="password" />
              </div>
            </div>
            <DialogFooter>
              <Button onClick={handleCreateProfile} className="bg-[var(--color-neon-cyan)] text-black hover:bg-[var(--color-neon-cyan)]/80">Save Profile</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pb-8">
         <AnimatePresence>
             {profiles.map((p) => (
                 <motion.div
                     key={p.id}
                     layout
                     initial={{ opacity: 0, y: 20 }}
                     animate={{ opacity: 1, y: 0 }}
                     exit={{ opacity: 0, scale: 0.9 }}
                     className="group relative flex flex-col p-5 rounded-xl border border-border/40 bg-card/10 hover:bg-card/30 hover:border-[var(--color-neon-cyan)]/50 transition-all duration-300"
                 >
                     <div className="flex justify-between items-start mb-4">
                         <div className="flex items-center gap-3">
                             <div className="p-2 rounded-md bg-[var(--color-neon-cyan)]/10 text-[var(--color-neon-cyan)] group-hover:bg-[var(--color-neon-cyan)]/20 transition-colors">
                                 <Shield size={20} />
                             </div>
                             <h3 className="font-semibold text-lg">{p.name}</h3>
                         </div>
                         <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity">
                             <Trash2 size={16} />
                         </Button>
                     </div>
                     
                     <div className="space-y-2 text-sm text-muted-foreground/80 font-mono">
                         <div className="flex items-center gap-2">
                             <Server size={14} className="text-muted-foreground" />
                             <span className="truncate">{p.server}:{p.port}</span>
                         </div>
                         <div className="flex items-center gap-2">
                             <Globe size={14} className="text-muted-foreground" />
                             <span className="uppercase">{p.protocol}</span>
                         </div>
                         {p.uuid && (
                             <div className="flex items-center gap-2">
                                 <Key size={14} className="text-muted-foreground" />
                                 <span className="truncate text-xs">{p.uuid.substring(0, 8)}...</span>
                             </div>
                         )}
                     </div>
                 </motion.div>
             ))}
         </AnimatePresence>
         
         {profiles.length === 0 && (
             <div className="col-span-full py-16 flex flex-col items-center justify-center text-muted-foreground/50 border border-dashed border-border/60 rounded-xl">
                 <Shield className="w-12 h-12 mb-4 opacity-20" />
                 <p className="font-mono text-sm">No profiles found. Create one securely.</p>
             </div>
         )}
      </div>
    </motion.div>
  );
}
