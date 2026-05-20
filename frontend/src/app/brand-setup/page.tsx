import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";

import { BrandSetupForm } from "@/components/ai/BrandSetupForm";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { authOptions } from "@/lib/auth";

export default async function BrandSetupPage() {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/login");

  return (
    <DashboardLayout title="Brand Setup">
      <BrandSetupForm />
    </DashboardLayout>
  );
}
