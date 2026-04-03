import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";

import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ExportsLibrary } from "@/components/exports/ExportsLibrary";
import { authOptions } from "@/lib/auth";
import { Export } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchWithAuth(path: string, token: string) {
  return fetch(`${API_URL}${path}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });
}

export default async function ExportsPage() {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/login");

  const token = (session as any)?.accessToken;
  if (!token) redirect("/login");

  const exportsRes = await fetchWithAuth("/api/exports", token);
  if (!exportsRes.ok) {
    throw new Error("Failed to load exports");
  }
  const exports = (await exportsRes.json()) as Export[];

  return (
    <DashboardLayout title="Exports">
      <ExportsLibrary initialExports={exports} />
    </DashboardLayout>
  );
}
