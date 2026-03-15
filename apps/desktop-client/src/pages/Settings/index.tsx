import { motion } from "framer-motion";

export function SettingsPage() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 1.05 }}
      transition={{ duration: 0.2 }}
      className="flex flex-col h-full"
    >
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Settings</h1>
        <p className="text-muted-foreground mt-2">Configure core app preferences and routing.</p>
      </header>
      
      <div className="flex-1 flex items-center justify-center border border-dashed border-border/60 rounded-xl bg-card/10">
         <p className="text-muted-foreground/50 font-mono text-sm">Settings panel (Routing, Core, UI)</p>
      </div>
    </motion.div>
  );
}
