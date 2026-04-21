import { Suspense } from "react";
import SigninForm from "@/components/auth/SigninForm";

export const metadata = {
  title: "Sign In",
};

export default function AuthPage() {
  return (
    <Suspense>
      <SigninForm />
    </Suspense>
  );
}
