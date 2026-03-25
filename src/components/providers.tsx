"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { HeroUIProvider } from "@heroui/react";
import { Toaster } from "sonner";
import { useSession } from "@/lib/auth-client";
import { FullscreenLoader } from "@/components/fullscreen-loader";

const PUBLIC_ROUTES = ["/", "/auth"];

function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { data: session, isPending } = useSession();

  const isPublicRoute = PUBLIC_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(route + "/")
  );

  useEffect(() => {
    if (!isPending && !session && !isPublicRoute) {
      router.push("/auth");
    }
  }, [isPending, session, isPublicRoute, router]);

  if (isPending && !isPublicRoute) {
    return <FullscreenLoader />;
  }

  if (!isPending && !session && !isPublicRoute) {
    return <FullscreenLoader />;
  }

  return <>{children}</>;
}

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <HeroUIProvider>
      <AuthGuard>{children}</AuthGuard>
      <Toaster
        position="top-right"
        expand={false}
        richColors
        closeButton
        theme="dark"
        toastOptions={{
          style: {
            background: "#1a1a2e",
            border: "1px solid #2a2a4a",
            color: "#fff",
          },
        }}
      />
    </HeroUIProvider>
  );
}
