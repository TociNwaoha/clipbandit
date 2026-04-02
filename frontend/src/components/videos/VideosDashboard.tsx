"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { UploadModal } from "@/components/upload/UploadModal";
import { VideoList } from "@/components/videos/VideoList";
import { useVideos } from "@/hooks/useVideos";

export function VideosDashboard() {
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const { videos, loading, error, refresh } = useVideos();

  return (
    <>
      <div className="mb-6 flex items-center justify-between gap-4">
        <h2 className="text-2xl font-semibold text-white">Videos</h2>
        <Button onClick={() => setIsUploadOpen(true)}>Upload Video</Button>
      </div>

      <VideoList
        videos={videos}
        loading={loading}
        error={error}
        onRefresh={refresh}
        onOpenUpload={() => setIsUploadOpen(true)}
      />

      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploaded={refresh}
      />
    </>
  );
}
