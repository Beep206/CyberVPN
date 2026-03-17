import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { invoke } from "@tauri-apps/api/core";
import { toast } from "sonner";
import { Cloud, CloudUpload, CloudDownload, RefreshCw, KeyRound, QrCode, Trash2, Smartphone } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";

export function AccountPage() {
  const [syncPassword, setSyncPassword] = useState("");
  const [hasSavedPassword, setHasSavedPassword] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState<"synced" | "unsynced">("unsynced");
  const [pairingToken, setPairingToken] = useState("");

  useEffect(() => {
    checkSavedPassword();
  }, []);

  const checkSavedPassword = async () => {
    try {
      const saved = await invoke<string>("get_sync_password");
      if (saved) {
        setSyncPassword(saved);
        setHasSavedPassword(true);
        generateQr(saved);
      }
    } catch (e) {
      setHasSavedPassword(false);
    }
  };

  const generateQr = async (pass: string) => {
    try {
      const token = await invoke<string>("generate_pairing_qr", { password: pass });
      setPairingToken(token);
    } catch (e) {
      console.error("Failed to generate QR token", e);
    }
  };

  const handleSavePassword = async () => {
    if (!syncPassword) return;
    try {
      await invoke("save_sync_password", { password: syncPassword });
      setHasSavedPassword(true);
      generateQr(syncPassword);
      toast.success("Sync Password saved securely in native Keyring");
    } catch (e) {
      toast.error(`Failed to save password: ${e}`);
    }
  };

  const handleDeletePassword = async () => {
    try {
      await invoke("delete_sync_password");
      setHasSavedPassword(false);
      setSyncPassword("");
      setPairingToken("");
      toast.success("Sync Password forgotten");
    } catch (e) {
      toast.error(`Failed to delete password: ${e}`);
    }
  };

  const handleCloudPush = async () => {
    if (!hasSavedPassword || isSyncing) return;
    setIsSyncing(true);
    
    try {
      await invoke("cloud_push", { password: syncPassword });
      setSyncStatus("synced");
      toast.success("Cloud Sync Complete: Data Pushed");
    } catch (e) {
      toast.error(`Push Failed: ${e}`);
      setSyncStatus("unsynced");
    } finally {
      setIsSyncing(false);
    }
  };

  const handleCloudPull = async () => {
    if (!hasSavedPassword || isSyncing) return;
    setIsSyncing(true);
    toast.info("Pulling data from cloud...");
    
    try {
      await invoke("cloud_pull", { password: syncPassword });
      setSyncStatus("synced");
      toast.success("Cloud Sync Complete: Data Pulled");
    } catch (e) {
      toast.error(`Pull Failed: ${e}`);
      setSyncStatus("unsynced");
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.3 }}
      className="max-w-4xl mx-auto space-y-8"
    >
      <div>
        <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-[var(--color-matrix-green)] to-[var(--color-neon-cyan)] bg-clip-text text-transparent flex items-center gap-3">
          <Cloud size={32} className="text-[var(--color-matrix-green)]" />
          My Ecosystem
        </h1>
        <p className="text-muted-foreground mt-2">
          End-to-end encrypted synchronization. Securely manage your VPN configurations across devices.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Left Column: Cloud Operations & Setup */}
        <div className="space-y-6">
          
          {/* Status Card */}
          <div className="p-6 rounded-2xl border border-border/50 bg-card/30 relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-b from-white/[0.02] to-transparent pointer-events-none" />
            
            <div className="flex items-center justify-between mb-8">
              <div className="flex items-center gap-3">
                 <div className="relative">
                   <Cloud className={`${syncStatus === "synced" ? "text-[var(--color-matrix-green)]" : "text-muted-foreground"}`} size={28} />
                   {syncStatus === "synced" && (
                     <span className="absolute -top-1 -right-1 flex h-3 w-3">
                       <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--color-matrix-green)] opacity-75"></span>
                       <span className="relative inline-flex rounded-full h-3 w-3 bg-[var(--color-matrix-green)]"></span>
                     </span>
                   )}
                 </div>
                 <div>
                   <h3 className="font-semibold">{syncStatus === "synced" ? "Cloud Connected" : "Local Changes Unsynced"}</h3>
                   <p className="text-xs text-muted-foreground">E2EE Data Synchronization</p>
                 </div>
              </div>
            </div>

            <div className="flex justify-between gap-4">
               <motion.button
                 whileHover={hasSavedPassword ? { scale: 1.05 } : {}}
                 whileTap={hasSavedPassword ? { scale: 0.95 } : {}}
                 disabled={!hasSavedPassword || isSyncing}
                 onClick={handleCloudPush}
                 className="flex-1 flex flex-col items-center justify-center gap-2 p-4 rounded-xl bg-black/40 border border-border/50 transition-colors hover:border-[var(--color-neon-cyan)]/50 disabled:opacity-50 disabled:hover:border-border/50"
               >
                  {isSyncing ? (
                    <RefreshCw size={24} className="text-[var(--color-neon-cyan)] animate-spin" />
                  ) : (
                    <CloudUpload size={24} className="text-[var(--color-neon-cyan)]" />
                  )}
                  <span className="text-sm font-medium">Backup to Cloud</span>
               </motion.button>

               <motion.button
                 whileHover={hasSavedPassword ? { scale: 1.05 } : {}}
                 whileTap={hasSavedPassword ? { scale: 0.95 } : {}}
                 disabled={!hasSavedPassword || isSyncing}
                 onClick={handleCloudPull}
                 className="flex-1 flex flex-col items-center justify-center gap-2 p-4 rounded-xl bg-black/40 border border-border/50 transition-colors hover:border-[var(--color-matrix-green)]/50 disabled:opacity-50 disabled:hover:border-border/50"
               >
                  {isSyncing ? (
                    <RefreshCw size={24} className="text-[var(--color-matrix-green)] animate-spin" />
                  ) : (
                    <CloudDownload size={24} className="text-[var(--color-matrix-green)]" />
                  )}
                  <span className="text-sm font-medium">Pull from Cloud</span>
               </motion.button>
            </div>
          </div>

          {/* Encryption Setup */}
          <div className="p-6 rounded-2xl border border-border/50 bg-black/20">
             <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <KeyRound size={18} className="text-[var(--color-neon-pink)]" />
                Sync Password
             </h3>
             <p className="text-xs text-muted-foreground mb-4 leading-relaxed">
                Your data is AES-GCM encrypted locally before transit. The server never sees your passwords.
             </p>

             {!hasSavedPassword ? (
                <div className="space-y-4">
                  <input
                    type="password"
                    placeholder="Enter an Encryption Password..."
                    value={syncPassword}
                    onChange={(e) => setSyncPassword(e.target.value)}
                    className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-[var(--color-neon-pink)] transition-colors"
                  />
                  <button 
                    onClick={handleSavePassword}
                    className="w-full bg-[var(--color-neon-pink)]/20 text-[var(--color-neon-pink)] border border-[var(--color-neon-pink)]/50 rounded-md py-2 font-medium hover:bg-[var(--color-neon-pink)]/30 transition-colors"
                  >
                     Unlock Sync Ecosystem
                  </button>
                </div>
             ) : (
                <div className="flex items-center justify-between p-3 rounded bg-black/40 border border-green-500/30">
                   <div className="flex items-center gap-2 text-green-400">
                      <KeyRound size={16} />
                      <span className="text-sm font-medium">Key Securely Saved</span>
                   </div>
                   <button 
                     onClick={handleDeletePassword}
                     className="text-red-400 hover:text-red-300 transition-colors flex items-center gap-1 text-sm"
                   >
                     <Trash2 size={14} /> Clear Key
                   </button>
                </div>
             )}
          </div>
        </div>

        {/* Right Column: Handover / Device Pairing */}
        <div className="space-y-6">
           <div className="h-full p-8 rounded-2xl border border-border/50 bg-black/40 flex flex-col items-center justify-center text-center relative overflow-hidden group">
              <div className="w-16 h-16 rounded-full bg-[var(--color-neon-cyan)]/10 flex items-center justify-center mb-4">
                 <Smartphone size={32} className="text-[var(--color-neon-cyan)]" />
              </div>

              <h3 className="text-xl font-bold mb-2">Device Handover Pairing</h3>
              <p className="text-xs text-muted-foreground max-w-[260px] mx-auto mb-8">
                 Scan this QR code with the CyberVPN mobile or TV app to instantly synchronize.
              </p>

              {pairingToken ? (
                <div className="p-4 bg-white rounded-xl shadow-[0_0_30px_rgba(0,255,255,0.1)] transition-transform duration-500 hover:scale-105 inline-block">
                  <QRCodeSVG 
                    value={pairingToken}
                    size={200}
                    level="H"
                    includeMargin={false}
                    fgColor="#000000"
                    bgColor="#ffffff"
                    imageSettings={{
                      src: "/icon.png", // Tauri default icon
                      x: undefined,
                      y: undefined,
                      height: 48,
                      width: 48,
                      excavate: true,
                    }}
                  />
                </div>
              ) : (
                <div className="w-[200px] h-[200px] rounded-xl border-2 border-dashed border-muted-foreground/30 flex flex-col items-center justify-center text-muted-foreground p-6">
                   <QrCode size={48} className="mb-2 opacity-50" />
                   <span className="text-xs font-medium">Set a Sync Password first</span>
                </div>
              )}
           </div>
        </div>
      </div>
    </motion.div>
  );
}
