"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

export function ShareButton({ url }: { url: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <Button size="sm" variant="outline" onClick={copy}>
      {copied ? "Copied" : "Share"}
    </Button>
  );
}
