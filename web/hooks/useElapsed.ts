"use client";

import { useEffect, useState } from "react";

/** Whole seconds since `running` turned true; resets to 0 when it turns false. */
export function useElapsed(running: boolean): number {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    if (!running) {
      setSeconds(0);
      return;
    }
    const start = Date.now();
    setSeconds(0);
    const id = setInterval(() => setSeconds(Math.floor((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(id);
  }, [running]);

  return seconds;
}
