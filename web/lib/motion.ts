import type { Transition, Variants } from "framer-motion";

// One easing curve for the whole UI (iOS-style, settles quickly without bounce).
export const EASE = [0.32, 0.72, 0, 1] as const;

export const transition = (reduce: boolean | null): Transition =>
  reduce ? { duration: 0 } : { duration: 0.28, ease: EASE };

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0 },
};

export const stagger = (reduce: boolean | null, step = 0.05): Variants => ({
  hidden: {},
  show: { transition: reduce ? { duration: 0 } : { staggerChildren: step, delayChildren: 0.04 } },
});
