import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { desktopMotionEase, useDesktopMotionBudget } from "../shared/lib/motion";

type RouteTransitionProps = {
  routeKey: string;
  children: ReactNode;
};

export function RouteTransition({ routeKey, children }: RouteTransitionProps) {
  const { prefersReducedMotion, durations, offsets } = useDesktopMotionBudget();

  return (
    <motion.div
      key={routeKey}
      initial={{ opacity: 0, y: offsets.route }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: durations.route,
        ease: desktopMotionEase,
      }}
      className="min-h-full will-change-[opacity,transform]"
      style={prefersReducedMotion ? undefined : { transformOrigin: "top center" }}
    >
      {children}
    </motion.div>
  );
}
