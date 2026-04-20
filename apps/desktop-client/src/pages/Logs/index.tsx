import { motion } from "framer-motion";
import { Bug } from "lucide-react";
import { DiagnosticsSupportPanel } from "../../components/settings/diagnostics-support-panel";
import { desktopMotionEase, useDesktopMotionBudget } from "../../shared/lib/motion";
import { useTranslation } from "react-i18next";

export function LogsPage() {
  const { t } = useTranslation();
  const { prefersReducedMotion, durations, offsets } = useDesktopMotionBudget();

  return (
    <motion.div
      initial={{ opacity: 0, y: offsets.page }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: prefersReducedMotion ? 0 : -4 }}
      transition={{ duration: durations.page, ease: desktopMotionEase }}
      className="max-w-6xl mx-auto space-y-6"
    >
      <header className="flex justify-between items-end border-b border-white/5 pb-4 mb-8">
        <div>
          <h1
            className="text-4xl font-extrabold tracking-tighter text-[var(--color-neon-cyan)] uppercase"
            style={{ textShadow: "0 0 15px rgba(0,255,255,0.4)" }}
          >
            {t("logs.title")}
          </h1>
          <p className="text-muted-foreground font-mono text-sm mt-2 flex items-center gap-2">
            <Bug className="text-[var(--color-neon-cyan)]" size={16} /> {t("logs.description")}
          </p>
        </div>
      </header>

      <DiagnosticsSupportPanel />
    </motion.div>
  );
}
