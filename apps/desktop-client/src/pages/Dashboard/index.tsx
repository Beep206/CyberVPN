import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ConnectButton } from "../../widgets/ConnectButton";
import { TrafficGraph } from "../../widgets/TrafficGraph";
import { toast } from "sonner";
import { 
    ConnectionStatus, 
    getConnectionStatus, 
    listenConnectionStatus, 
    listenTrafficUpdate,
    connectProfile, 
    getProfiles,
    disconnectProxy 
} from "../../shared/api/ipc";

export function DashboardPage() {
  const [status, setStatus] = useState<ConnectionStatus>({
      status: "disconnected",
      upBytes: 0,
      downBytes: 0
  });

  const [trafficData, setTrafficData] = useState<Array<{ time: string, up: number, down: number }>>([]);

  useEffect(() => {
    // Initial fetch
    getConnectionStatus().then(setStatus).catch(console.error);

    // Setup listener
    const setupListener = async () => {
        const unlistenStatus = await listenConnectionStatus((newStatus) => {
            setStatus(newStatus);
            
            // Only add data points if we are connected
            if (newStatus.status === "connected") {
                setTrafficData(prev => {
                    const now = new Date().toLocaleTimeString();
                    const newData = [...prev, { time: now, up: newStatus.upBytes, down: newStatus.downBytes }];
                    // Keep last 30 data points
                    return newData.length > 30 ? newData.slice(newData.length - 30) : newData;
                });
            } else if (newStatus.status === "disconnected") {
                // Clear graph on disconnect
                setTrafficData([]);
            }
        });
        const unlistenTraffic = await listenTrafficUpdate((data) => {
            setTrafficData(prev => {
                const now = new Date().toLocaleTimeString();
                const newData = [...prev, { time: now, up: data.up, down: data.down }];
                return newData.length > 30 ? newData.slice(newData.length - 30) : newData;
            });
            setStatus(current => ({ ...current, upBytes: data.up, downBytes: data.down }));
        });
        
        return () => {
            unlistenStatus();
            unlistenTraffic();
        };
    };
    
    let unlistenFn: (() => void) | undefined;
    setupListener().then(fn => { unlistenFn = fn; });
    
    return () => {
        if (unlistenFn) unlistenFn();
    };
  }, []);

  const handleConnect = async () => {
      try {
          const profiles = await getProfiles();
          if (profiles.length === 0) {
              toast.error("No profiles available. Please add one in Profiles first.");
              return;
          }
          setStatus(prev => ({ ...prev, status: "connecting" }));
          await connectProfile(profiles[0].id);
      } catch (e: any) {
          console.error("Failed to connect", e);
          toast.error(`Connection failed: ${e}`);
          setStatus(prev => ({ ...prev, status: "error" }));
      }
  };

  const handleDisconnect = async () => {
      try {
          await disconnectProxy();
      } catch (e) {
          console.error("Failed to disconnect", e);
      }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 1.05 }}
      transition={{ duration: 0.2 }}
      className="flex flex-col h-full gap-12"
    >
      <header className="flex items-center justify-between">
        <div>
           <h1 className="text-4xl font-black tracking-tighter uppercase text-[var(--color-matrix-green)] drop-shadow-[0_0_8px_rgba(0,255,136,0.6)]">
               Terminal
           </h1>
           <p className="text-muted-foreground mt-1 font-mono text-sm tracking-widest">
               STATUS: {status.status.toUpperCase()}
           </p>
        </div>
      </header>
      
      <div className="flex-1 flex flex-col items-center justify-center gap-16">
         {/* Central Connect Button */}
         <ConnectButton 
             status={status} 
             onConnect={handleConnect} 
             onDisconnect={handleDisconnect} 
         />

         {/* Traffic Graph */}
         <div className="w-full max-w-3xl">
             <TrafficGraph data={trafficData} />
         </div>
      </div>
    </motion.div>
  );
}
