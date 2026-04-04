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

  let exports: Export[] = [];
  let initialError: string | null = null;

  try {
    const exportsRes = await fetchWithAuth("/api/exports", token);
    if (exportsRes.status === 401 || exportsRes.status === 403) {
      redirect("/login");
    }
    if (!exportsRes.ok) {
      let detail = "Failed to load exports";
      try {
        const body = await exportsRes.json();
        if (body?.detail && typeof body.detail === "string") {
          detail = body.detail;
        }
      } catch {
        // Keep default error message when response is not JSON.
      }
      initialError = detail;
    } else {
      exports = (await exportsRes.json()) as Export[];
    }
  } catch {
    initialError = "Failed to load exports";
  }

  return (
    <DashboardLayout title="Exports">
      <ExportsLibrary initialExports={exports} initialError={initialError} />
    </DashboardLayout>
  );
}
