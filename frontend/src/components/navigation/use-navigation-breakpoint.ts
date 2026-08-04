"use client";

import { useEffect, useState } from "react";

export type Breakpoint = "mobile" | "tablet" | "desktop";

const QUERIES = {
  mobile: "(max-width: 767px)",
  tablet: "(min-width: 768px) and (max-width: 1023px)",
  desktop: "(min-width: 1024px)",
};

function getBreakpoint(): Breakpoint {
  if (typeof window === "undefined") {
    return "desktop";
  }
  if (window.matchMedia(QUERIES.mobile).matches) {
    return "mobile";
  }
  if (window.matchMedia(QUERIES.tablet).matches) {
    return "tablet";
  }
  return "desktop";
}

export function useNavigationBreakpoint(): Breakpoint {
  const [bp, setBp] = useState<Breakpoint>("desktop");

  useEffect(() => {
    setBp(getBreakpoint());
    const handlers: Array<{ mq: MediaQueryList; fn: () => void }> = [];
    const update = () => setBp(getBreakpoint());
    for (const q of Object.values(QUERIES)) {
      const mq = window.matchMedia(q);
      mq.addEventListener("change", update);
      handlers.push({ mq, fn: update });
    }
    return () => {
      for (const { mq, fn } of handlers) {
        mq.removeEventListener("change", fn);
      }
    };
  }, []);

  return bp;
}

export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const fn = () => setReduced(mq.matches);
    mq.addEventListener("change", fn);
    return () => mq.removeEventListener("change", fn);
  }, []);

  return reduced;
}
