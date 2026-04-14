"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { FullVideoExportResponse, VideoListItem } from "@/types";

interface VideoListProps {
  videos: VideoListItem[];
  loading: boolean;
  error: string | null;
  onRefresh: () => Promise<void> | void;
  onOpenUpload: () => void;
}

const statusStyles: Record<string, string> = {
  queued: "bg-slate-700/80 text-slate-200",
  downloading: "bg-blue-500/20 text-blue-300 animate-pulse",
  transcribing: "bg-blue-500/20 text-blue-300 animate-pulse",
  scoring: "bg-purple-500/20 text-purple-300 animate-pulse",
  ready: "bg-emerald-500/20 text-emerald-300",
  error: "bg-red-500/20 text-red-300",
};

function formatDuration(seconds: number | null): string | null {
  if (!seconds || seconds <= 0) return null;
  const totalMinutes = Math.max(1, Math.round(seconds / 60));
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function formatRelativeTime(isoDate: string): string {
  const now = Date.now();
  const then = new Date(isoDate).getTime();
  const deltaSec = Math.round((then - now) / 1000);

  const units: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ["year", 60 * 60 * 24 * 365],
    ["month", 60 * 60 * 24 * 30],
    ["day", 60 * 60 * 24],
    ["hour", 60 * 60],
    ["minute", 60],
  ];

  const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  for (const [unit, unitSeconds] of units) {
    if (Math.abs(deltaSec) >= unitSeconds) {
      return rtf.format(Math.round(deltaSec / unitSeconds), unit);
    }
  }
  return "just now";
}

function statusLabel(status: string): string {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export function VideoList({ videos, loading, error, onRefresh, onOpenUpload }: VideoListProps) {
  const router = useRouter();
  const [menuVideoId, setMenuVideoId] = useState<string | null>(null);
  const [deletingVideoId, setDeletingVideoId] = useState<string | null>(null);
  const [preparingVideoId, setPreparingVideoId] = useState<string | null>(null);
  const [failedThumbnailUrls, setFailedThumbnailUrls] = useState<Record<string, boolean>>({});
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const sortedVideos = useMemo(
    () => [...videos].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
    [videos]
  );

  const handleDeleteVideo = async (videoId: string) => {
    if (deletingVideoId) return;
    setDeletingVideoId(videoId);
    setDeleteError(null);
    setActionMessage(null);
    try {
      await api.delete(`/api/videos/${videoId}`);
      await onRefresh();
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Failed to delete video";
      setDeleteError(message);
    } finally {
      setDeletingVideoId(null);
      setMenuVideoId(null);
    }
  };

  const handlePrepareFullExport = async (videoId: string) => {
    if (preparingVideoId) return;
    setPreparingVideoId(videoId);
    setDeleteError(null);
    setActionMessage(null);
    try {
      const payload = await api.post<FullVideoExportResponse>(`/api/social/videos/${videoId}/full-export`, {});
      setActionMessage(
        payload.reused_existing_export
          ? "Reused existing full export and opened clip editor."
          : "Prepared full export and opened clip editor."
      );
      router.push(`/videos/${videoId}/clips/${payload.clip_id}`);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Failed to prepare full export";
      setDeleteError(message);
    } finally {
      setPreparingVideoId(null);
    }
  };

  if (loading) {
    return (
      <Card className="min-h-72 flex items-center justify-center">
        <div className="flex items-center gap-3 text-slate-300">
          <LoadingSpinner />
          Loading videos...
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="min-h-72 flex flex-col items-center justify-center text-center">
        <p className="text-red-400">{error}</p>
        <Button onClick={() => void onRefresh()} className="mt-4">
          Retry
        </Button>
      </Card>
    );
  }

  if (!sortedVideos.length) {
    return (
      <Card className="min-h-80 flex flex-col items-center justify-center text-center">
        <p className="text-2xl font-semibold text-white">No videos yet</p>
        <p className="mt-2 text-slate-400">Upload a video or import from YouTube to get started</p>
        <Button className="mt-6" onClick={onOpenUpload}>
          Get Started
        </Button>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {actionMessage && <p className="text-sm text-emerald-300">{actionMessage}</p>}
      {deleteError && <p className="text-sm text-red-400">{deleteError}</p>}
      {sortedVideos.map((video) => {
        const thumbnailUrl = video.thumbnail_url;
        const showThumbnail = Boolean(thumbnailUrl && !failedThumbnailUrls[thumbnailUrl]);

        return (
        <Card key={video.id} className="relative">
          <div className="flex items-start gap-4">
            <Link href={`/videos/${video.id}`} className="flex min-w-0 flex-1 items-start gap-4 group">
              {showThumbnail ? (
                <img
                  src={thumbnailUrl!}
                  alt={video.title ? `${video.title} thumbnail` : "Video thumbnail"}
                  className="h-20 w-36 rounded-lg border border-slate-600 object-cover flex-shrink-0 bg-slate-700/60 group-hover:border-[#7C3AED]/70 transition-colors"
                  onError={() => {
                    if (!thumbnailUrl) return;
                    setFailedThumbnailUrls((previous) =>
                      previous[thumbnailUrl] ? previous : { ...previous, [thumbnailUrl]: true }
                    );
                  }}
                />
              ) : (
                <div className="h-20 w-36 rounded-lg bg-slate-700/60 border border-slate-600 flex-shrink-0 group-hover:border-[#7C3AED]/70 transition-colors" />
              )}
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="truncate text-base font-semibold text-white group-hover:text-[#A78BFA] transition-colors">
                    {video.title || "Untitled video"}
                  </h3>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusStyles[video.status] || statusStyles.queued}`}>
                    {statusLabel(video.status)}
                  </span>
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-slate-400">
                  {formatDuration(video.duration_sec) && <span>{formatDuration(video.duration_sec)}</span>}
                  {video.clip_count > 0 && <span>{video.clip_count} clips</span>}
                  <span>{formatRelativeTime(video.created_at)}</span>
                </div>
                {video.status === "error" && video.error_message ? (
                  <p className="mt-2 text-xs text-red-300">{video.error_message}</p>
                ) : null}
              </div>
            </Link>

            <div className="flex flex-col items-end gap-2">
              {video.status === "ready" ? (
                <button
                  type="button"
                  onClick={() => void handlePrepareFullExport(video.id)}
                  disabled={preparingVideoId === video.id}
                  className="rounded-md border border-[#7C3AED]/40 bg-[#7C3AED]/10 px-3 py-1.5 text-xs font-medium text-[#C4B5FD] hover:bg-[#7C3AED]/20 disabled:opacity-50"
                >
                  {preparingVideoId === video.id ? "Preparing..." : "Prepare Full Export"}
                </button>
              ) : null}
              <div className="relative">
                <button
                  className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
                  onClick={() => setMenuVideoId(menuVideoId === video.id ? null : video.id)}
                  aria-label="More options"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <circle cx="5" cy="12" r="1.8" fill="currentColor" />
                    <circle cx="12" cy="12" r="1.8" fill="currentColor" />
                    <circle cx="19" cy="12" r="1.8" fill="currentColor" />
                  </svg>
                </button>
                {menuVideoId === video.id && (
                  <div className="absolute right-0 mt-1 w-28 rounded-lg border border-slate-700 bg-[#0F172A] p-1 shadow-xl">
                    <button
                      className="w-full rounded-md px-3 py-2 text-left text-sm text-red-300 hover:bg-red-500/10 disabled:opacity-50"
                      onClick={() => void handleDeleteVideo(video.id)}
                      disabled={deletingVideoId === video.id}
                    >
                      {deletingVideoId === video.id ? "Deleting..." : "Delete"}
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </Card>
      );
      })}
    </div>
  );
}
