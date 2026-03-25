"use client";

import { Loader2 } from "lucide-react";

export function FullscreenLoader() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  );
}
