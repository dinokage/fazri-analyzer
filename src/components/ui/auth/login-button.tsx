"use client";
import { Button } from "@/components/ui/button";
import { authClient } from "@/lib/auth-client";

export default function LoginButton(){
  const signInWithGoogle = async ()=>{
    await authClient.signIn.social({
      provider:"google",
      callbackURL:"/"
    })
  }
    return(
        <Button onClick={signInWithGoogle}>Login</Button>
    )
}