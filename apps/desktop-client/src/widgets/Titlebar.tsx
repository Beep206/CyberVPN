import { useEffect, useState } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { Minus, Square, X } from "lucide-react";
import { Shield } from "lucide-react";

export function Titlebar() {
  const [isMaximized, setIsMaximized] = useState(false);

  useEffect(() => {
    const handleResize = async () => {
      try {
        setIsMaximized(await getCurrentWindow().isMaximized());
      } catch (e) {
        // Handle gracefully if not in Tauri
      }
    };
    
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const minimize = () => getCurrentWindow().minimize();
  const toggleMaximize = async () => {
    try {
      const maximized = await getCurrentWindow().isMaximized();
      if (maximized) {
        getCurrentWindow().unmaximize();
        setIsMaximized(false);
      } else {
        getCurrentWindow().maximize();
        setIsMaximized(true);
      }
    } catch (e) {
      // Ignore
    }
  };
  const close = () => getCurrentWindow().close();

  return (
    <div 
      data-tauri-drag-region 
      className="h-10 flex justify-between items-center select-none bg-black/90 border-b border-white/5 text-muted-foreground fixed top-0 left-0 right-0 z-50 backdrop-blur-md"
    >
        <div className="flex items-center gap-2 px-3 pointer-events-none text-[var(--color-matrix-green)]">
            <Shield size={14} className="drop-shadow-[0_0_8px_var(--color-matrix-green)] opacity-80" />
            <span className="text-[10px] font-mono font-semibold tracking-widest opacity-90">CYBERVPN</span>
        </div>
      <div className="flex h-full pointer-events-auto">
        <div 
          className="inline-flex justify-center items-center w-12 h-full hover:bg-white/10 transition-colors cursor-default text-muted-foreground hover:text-white"
          onClick={minimize}
        >
          <Minus size={14} />
        </div>
        <div 
          className="inline-flex justify-center items-center w-12 h-full hover:bg-white/10 transition-colors cursor-default text-muted-foreground hover:text-white"
          onClick={toggleMaximize}
        >
          {isMaximized ? <Square size={12} className="opacity-80" /> : <Square size={12} />}
        </div>
        <div 
          className="inline-flex justify-center items-center w-12 h-full hover:bg-red-500 hover:text-white transition-colors cursor-default text-muted-foreground"
          onClick={close}
        >
          <X size={14} />
        </div>
      </div>
    </div>
  );
}
