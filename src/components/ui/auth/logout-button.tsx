"use client";
import { Button } from "@/components/ui/button";
import { authClient, useSession } from "@/lib/auth-client";
import { useRouter } from "next/navigation";

export default function LogOutButton() {
  const router = useRouter();
  const signOut = async () => {
    authClient.signOut().then(() => {
      router.push("/");
    });
  };
  return <Button onClick={signOut}>Sign Out</Button>;
}
