import LoginButton from "@/components/ui/auth/login-button";
import LogOutButton from "@/components/ui/auth/logout-button";
import { auth } from "@/lib/auth";
import { headers } from "next/headers";
export default async function Home() {
  const session = await auth.api.getSession({
    headers: await headers(),
  });
  return (
    <div>
      <h1>Home</h1>
      {!session ? (
        <LoginButton />
      ) : (
        <div>
          <h2>we present you our website. Mr. {session.user.name}</h2>
          <LogOutButton />
        </div>
      )}
    </div>
  );
}
