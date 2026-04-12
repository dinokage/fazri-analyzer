import { use, Suspense } from "react";
import SigninForm from "@/components/auth/SigninForm";

export const metadata = {
  title: "Sign In",
};

export default function AuthPage({
  searchParams,
}: {
  searchParams: Promise<{ college?: string }>;
}) {
  const params = use(searchParams);
  return (
    <Suspense>
      <SigninForm prefillSlug={params.college} />
    </Suspense>
  );
}
