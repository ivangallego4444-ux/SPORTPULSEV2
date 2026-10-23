"use client";

import { useEffect, useState } from "react";

export interface Countdown {
  days: number;
  hours: number;
  minutes: number;
  seconds: number;
  isPast: boolean;
}

function computeCountdown(target: Date): Countdown {
  const diffMs = target.getTime() - Date.now();
  if (diffMs <= 0) {
    return { days: 0, hours: 0, minutes: 0, seconds: 0, isPast: true };
  }
  const totalSeconds = Math.floor(diffMs / 1000);
  return {
    days: Math.floor(totalSeconds / 86400),
    hours: Math.floor((totalSeconds % 86400) / 3600),
    minutes: Math.floor((totalSeconds % 3600) / 60),
    seconds: totalSeconds % 60,
    isPast: false,
  };
}

export function useCountdown(targetIso: string | null): Countdown | null {
  const [countdown, setCountdown] = useState<Countdown | null>(() =>
    targetIso ? computeCountdown(new Date(targetIso)) : null
  );

  useEffect(() => {
    if (!targetIso) {
      setCountdown(null);
      return;
    }
    const target = new Date(targetIso);
    setCountdown(computeCountdown(target));
    const interval = setInterval(() => setCountdown(computeCountdown(target)), 1000);
    return () => clearInterval(interval);
  }, [targetIso]);

  return countdown;
}
