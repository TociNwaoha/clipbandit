import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";

import { SlideEditor } from "@/components/carousels/SlideEditor";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { authOptions } from "@/lib/auth";

export default async function NewCarouselPage({
  searchParams,
}: {
  searchParams?: { template?: string };
}) {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/login");

  const initialTemplateId = typeof searchParams?.template === "string" ? searchParams.template : undefined;

  return (
    <DashboardLayout title="New Carousel">
      <SlideEditor initialTemplateId={initialTemplateId} />
    </DashboardLayout>
  );
}
