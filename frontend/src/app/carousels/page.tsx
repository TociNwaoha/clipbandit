import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";

import { TemplateGallery } from "@/components/carousels/TemplateGallery";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { authOptions } from "@/lib/auth";

export default async function CarouselsPage() {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/login");

  return (
    <DashboardLayout title="Carousels">
      <div className="space-y-5">
        <div>
          <h2 className="text-2xl font-semibold text-[var(--app-text)]">Carousel Templates</h2>
          <p className="mt-1 text-sm text-[var(--app-muted)]">
            Choose a style, generate slide copy, edit content, then render and export PNG slides.
          </p>
        </div>
        <TemplateGallery />
      </div>
    </DashboardLayout>
  );
}
