import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";

import { ContentQueueDashboard } from "@/components/ai/ContentQueueDashboard";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { authOptions } from "@/lib/auth";

export default async function ContentQueuePage() {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/login");

  return (
    <DashboardLayout title="Content Queue">
      <ContentQueueDashboard />
    </DashboardLayout>
  );
}
