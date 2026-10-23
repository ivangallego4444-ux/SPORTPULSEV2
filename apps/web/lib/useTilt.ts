"use client";

import { useMotionValue, useSpring, useTransform } from "framer-motion";
import type { MouseEvent } from "react";

/** Real mousemove-driven 3D tilt (rotateX/rotateY) for a card — no
 * canvas/WebGL needed, pure CSS 3D transforms via Framer Motion. */
export function useTilt(maxDegrees = 10) {
  const x = useMotionValue(0.5);
  const y = useMotionValue(0.5);

  const rotateX = useSpring(useTransform(y, [0, 1], [maxDegrees, -maxDegrees]), {
    stiffness: 300,
    damping: 25,
  });
  const rotateY = useSpring(useTransform(x, [0, 1], [-maxDegrees, maxDegrees]), {
    stiffness: 300,
    damping: 25,
  });

  function onMouseMove(event: MouseEvent<HTMLElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    x.set((event.clientX - rect.left) / rect.width);
    y.set((event.clientY - rect.top) / rect.height);
  }

  function onMouseLeave() {
    x.set(0.5);
    y.set(0.5);
  }

  return { rotateX, rotateY, onMouseMove, onMouseLeave };
}
