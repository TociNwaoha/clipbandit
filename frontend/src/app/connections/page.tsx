import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";

import { ConnectionsPanel } from "@/components/connections/ConnectionsPanel";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { authOptions } from "@/lib/auth";

export default async function ConnectionsPage() {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/login");

  return (
    <DashboardLayout title="Connections">
      <ConnectionsPanel />
    </DashboardLayout>
  );
}
