import { redirect } from "next/navigation";

export default function CustomDomainPage() {
  redirect("/dashboard/settings/branding?tab=custom-domain");
}
