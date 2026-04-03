import { getServerSession } from "next-auth";
import { notFound, redirect } from "next/navigation";

import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ClipEditorPanel } from "@/components/videos/ClipEditorPanel";
import { authOptions } from "@/lib/auth";
import { Clip, Export, Video } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchWithAuth(path: string, token: string) {
  return fetch(`${API_URL}${path}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });
}

interface PageProps {
  params: {
    id: string;
    clipId: string;
  };
}

export default async function ClipEditorPage({ params }: PageProps) {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/login");

  const token = (session as any)?.accessToken;
  if (!token) redirect("/login");

  const [videoRes, clipRes, exportsRes] = await Promise.all([
    fetchWithAuth(`/api/videos/${params.id}`, token),
    fetchWithAuth(`/api/clips/${params.clipId}`, token),
    fetchWithAuth(`/api/exports?clip_id=${encodeURIComponent(params.clipId)}`, token),
  ]);

  if (videoRes.status === 404 || clipRes.status === 404) {
    notFound();
  }
  if (!videoRes.ok) throw new Error("Failed to load video");
  if (!clipRes.ok) throw new Error("Failed to load clip");

  const video = (await videoRes.json()) as Video;
  const clip = (await clipRes.json()) as Clip;
  if (clip.video_id !== video.id) {
    notFound();
  }

  let exports: Export[] = [];
  if (exportsRes.ok) {
    exports = (await exportsRes.json()) as Export[];
  }

  return (
    <DashboardLayout title="Clip Review & Export">
      <ClipEditorPanel video={video} initialClip={clip} initialExports={exports} />
    </DashboardLayout>
  );
}
