import { getServerSession } from "next-auth";
import { notFound, redirect } from "next/navigation";

import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { VideoDetailPanel } from "@/components/videos/VideoDetailPanel";
import { authOptions } from "@/lib/auth";
import { Video, VideoTranscript } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchWithAuth(path: string, token: string) {
  return fetch(`${API_URL}${path}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });
}

export default async function VideoDetailPage({ params }: { params: { id: string } }) {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/login");

  const token = (session as any)?.accessToken;
  if (!token) redirect("/login");

  const videoRes = await fetchWithAuth(`/api/videos/${params.id}`, token);
  if (videoRes.status === 404) notFound();
  if (!videoRes.ok) throw new Error("Failed to load video");

  const video: Video = await videoRes.json();

  let transcript: VideoTranscript | null = null;
  let transcriptError: string | null = null;

  if (video.status === "scoring" || video.status === "ready") {
    const transcriptRes = await fetchWithAuth(`/api/videos/${params.id}/transcript`, token);
    if (transcriptRes.ok) {
      transcript = (await transcriptRes.json()) as VideoTranscript;
    } else {
      const body = await transcriptRes.json().catch(() => ({ detail: "Transcript not ready yet" }));
      transcriptError = body.detail || "Transcript not ready yet";
    }
  }

  return (
    <DashboardLayout title="Video Details">
      <VideoDetailPanel video={video} transcript={transcript} transcriptError={transcriptError} />
    </DashboardLayout>
  );
}
