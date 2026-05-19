import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";

import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ExportsLibrary } from "@/components/exports/ExportsLibrary";
import { authOptions } from "@/lib/auth";
import { SERVER_API_URL } from "@/lib/serverApi";
import { CarouselExport, Export } from "@/types";

async function fetchWithAuth(path: string, token: string) {
  return fetch(`${SERVER_API_URL}${path}`, {
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
  let carouselExports: CarouselExport[] = [];
  let initialError: string | null = null;

  try {
    const [exportsRes, carouselRes] = await Promise.all([
      fetchWithAuth("/api/exports", token),
      fetchWithAuth("/api/carousels/exports", token),
    ]);
    if (exportsRes.status === 401 || exportsRes.status === 403 || carouselRes.status === 401 || carouselRes.status === 403) {
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

    if (!carouselRes.ok) {
      if (!initialError) {
        let detail = "Failed to load carousel exports";
        try {
          const body = await carouselRes.json();
          if (body?.detail && typeof body.detail === "string") {
            detail = body.detail;
          }
        } catch {
          // Keep default error message when response is not JSON.
        }
        initialError = detail;
      }
    } else {
      carouselExports = (await carouselRes.json()) as CarouselExport[];
    }
  } catch {
    initialError = "Failed to load exports";
  }

  return (
    <DashboardLayout title="Exports">
      <ExportsLibrary
        initialExports={exports}
        initialCarouselExports={carouselExports}
        initialError={initialError}
      />
    </DashboardLayout>
  );
}
