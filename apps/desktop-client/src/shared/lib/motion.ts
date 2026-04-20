import { useReducedMotion } from "framer-motion";

export const desktopMotionEase: [number, number, number, number] = [0.22, 1, 0.36, 1];

export function useDesktopMotionBudget() {
  const prefersReducedMotion = useReducedMotion();

  return {
    prefersReducedMotion,
    durations: {
      route: prefersReducedMotion ? 0.01 : 0.14,
      page: prefersReducedMotion ? 0.01 : 0.18,
      list: prefersReducedMotion ? 0.01 : 0.14,
      micro: prefersReducedMotion ? 0.01 : 0.12,
      accent: prefersReducedMotion ? 0.01 : 0.18,
    },
    offsets: {
      route: prefersReducedMotion ? 0 : 6,
      page: prefersReducedMotion ? 0 : 8,
      list: prefersReducedMotion ? 0 : 10,
    },
    scales: {
      hover: prefersReducedMotion ? 1 : 1.01,
      tap: prefersReducedMotion ? 1 : 0.985,
    },
  };
}
