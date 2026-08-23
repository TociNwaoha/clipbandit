import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";

import { CardRequiredBetaWalkthrough } from "@/components/auth/CardRequiredBetaWalkthrough";
import { authOptions } from "@/lib/auth";

export default async function CardRequiredBetaWelcomePage() {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/login");
  return <CardRequiredBetaWalkthrough />;
}
