"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Card } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { Clip, Video, VideoTranscript } from "@/types";

type TabKey = "transcript" | "clips";

interface VideoDetailPanelProps {
  video: Video;
  transcript: VideoTranscript | null;
  transcriptError: string | null;
  clips: Clip[];
  clipsError: string | null;
}

const statusStyles: Record<string, string> = {
  queued: "bg-slate-700/80 text-slate-200",
  downloading: "bg-blue-500/20 text-blue-300 animate-pulse",
  transcribing: "bg-blue-500/20 text-blue-300 animate-pulse",
  scoring: "bg-purple-500/20 text-purple-300 animate-pulse",
  ready: "bg-emerald-500/20 text-emerald-300",
  error: "bg-red-500/20 text-red-300",
  metadata_extracting: "bg-blue-500/20 text-blue-300 animate-pulse",
  downloadable: "bg-blue-500/20 text-blue-300 animate-pulse",
  blocked: "bg-amber-500/20 text-amber-300",
  replacement_upload_required: "bg-amber-500/20 text-amber-300",
  helper_required: "bg-amber-500/20 text-amber-300",
  embed_only: "bg-slate-600/50 text-slate-200",
  failed_retryable: "bg-red-500/20 text-red-300",
  failed_terminal: "bg-red-500/20 text-red-300",
};

const YOUTUBE_SOURCE_TYPES = new Set(["youtube", "youtube_single", "youtube_playlist"]);
const BLOCKED_IMPORT_STATES = new Set([
  "blocked",
  "replacement_upload_required",
  "helper_required",
  "embed_only",
]);

function formatDuration(seconds: number | null): string {
  if (!seconds || seconds <= 0) return "Unknown";
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const remainderMinutes = minutes % 60;
  if (hours > 0) return `${hours}h ${remainderMinutes}m`;
  return `${minutes}m`;
}

function formatTimeBoundary(seconds: number): string {
  const safe = Math.max(0, Math.floor(seconds));
  const mins = Math.floor(safe / 60);
  const secs = safe % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

function formatClipDuration(seconds: number | null): string {
  if (!seconds || seconds <= 0) return "0s";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}m ${secs}s`;
}

function importStateLabel(state: string): string {
  return state
    .split(":")[0]
    .split("_")
    .filter(Boolean)
    .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))
    .join(" ");
}

export function VideoDetailPanel({ video, transcript, transcriptError, clips, clipsError }: VideoDetailPanelProps) {
  const [activeTab, setActiveTab] = useState<TabKey>("transcript");

  const transcriptText = useMemo(() => {
    if (!transcript) return "";
    return transcript.full_text || "";
  }, [transcript]);
  const isYoutubeSource = YOUTUBE_SOURCE_TYPES.has(video.source_type);
  const effectiveImportState = isYoutubeSource ? video.import_state : null;
  const displayStateKey =
    isYoutubeSource && effectiveImportState && effectiveImportState !== "processing"
      ? effectiveImportState
      : video.status;
  const displayStateLabel =
    isYoutubeSource && effectiveImportState && effectiveImportState !== "processing"
      ? importStateLabel(effectiveImportState)
      : video.status.charAt(0).toUpperCase() + video.status.slice(1);
  const isBlockedImport =
    Boolean(video.is_download_blocked) ||
    Boolean(effectiveImportState && BLOCKED_IMPORT_STATES.has(effectiveImportState));

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-xl font-semibold text-white">{video.title || "Untitled Video"}</h2>
          <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusStyles[displayStateKey] || statusStyles.queued}`}>
            {displayStateLabel}
          </span>
        </div>
        <div className="mt-4 flex flex-wrap gap-6 text-sm text-slate-300">
          <p>
            <span className="text-slate-500">Duration:</span> {formatDuration(video.duration_sec)}
          </p>
          <p>
            <span className="text-slate-500">Resolution:</span> {video.resolution || "Unknown"}
          </p>
          {video.source_type.startsWith("youtube") ? (
            <p>
              <span className="text-slate-500">Import mode:</span>{" "}
              {video.import_mode === "embed_only"
                ? "Embed only"
                : video.import_mode === "manual_upload"
                ? "Manual upload"
                : "Server download"}
            </p>
          ) : null}
        </div>
        {isBlockedImport ? (
          <p className="mt-3 text-xs text-amber-300">
            Server download was blocked for this source. You can keep it as embed reference or upload file manually.
          </p>
        ) : null}
      </Card>

      {video.source_download_url ? (
        <Card>
          <video
            className="w-full rounded-lg border border-slate-800 bg-black"
            controls
            playsInline
            preload="metadata"
            src={video.source_download_url}
          >
            Your browser does not support the video tag.
          </video>
        </Card>
      ) : video.embed_url ? (
        <Card>
          <div className="aspect-video w-full overflow-hidden rounded-lg border border-slate-800 bg-black">
            <iframe
              src={video.embed_url}
              title={video.title || "YouTube embed"}
              className="h-full w-full"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          </div>
        </Card>
      ) : null}

      <Card>
        <div className="mb-4 inline-flex rounded-lg bg-slate-900 p-1">
          <button
            className={`rounded-md px-4 py-2 text-sm transition-colors ${
              activeTab === "transcript" ? "bg-[#7C3AED] text-white" : "text-slate-300 hover:text-white"
            }`}
            onClick={() => setActiveTab("transcript")}
          >
            Transcript
          </button>
          <button
            className={`rounded-md px-4 py-2 text-sm transition-colors ${
              activeTab === "clips" ? "bg-[#7C3AED] text-white" : "text-slate-300 hover:text-white"
            }`}
            onClick={() => setActiveTab("clips")}
          >
            Clips
          </button>
        </div>

        {activeTab === "clips" && video.status === "scoring" && clips.length === 0 ? (
          <div className="flex items-center gap-3 rounded-lg border border-slate-700 bg-slate-900/40 p-6 text-slate-200">
            <LoadingSpinner />
            <p>Scoring clips... This usually completes shortly after transcription.</p>
          </div>
        ) : null}

        {activeTab === "clips" && clipsError ? (
          <div className="rounded-lg border border-red-900/60 bg-red-950/30 p-6 text-red-300">
            {clipsError}
          </div>
        ) : null}

        {activeTab === "clips" && !clipsError && video.status === "ready" && clips.length === 0 ? (
          <div className="rounded-lg border border-slate-700 bg-slate-900/40 p-6 text-slate-300">
            No strong clips found for this video yet.
          </div>
        ) : null}

        {activeTab === "clips" &&
        !clipsError &&
        clips.length === 0 &&
        ["queued", "downloading", "transcribing"].includes(video.status) ? (
          <div className="rounded-lg border border-slate-700 bg-slate-900/40 p-6 text-slate-300">
            Clips will appear after processing reaches scoring.
          </div>
        ) : null}

        {activeTab === "clips" && !clipsError && clips.length > 0 ? (
          <div className="space-y-4">
            {clips.map((clip, index) => (
              <div key={clip.id} className="rounded-lg border border-slate-700 bg-slate-900/40 p-4">
                <div className="flex gap-4">
                  {clip.thumbnail_url ? (
                    <img
                      src={clip.thumbnail_url}
                      alt={`Clip ${index + 1} thumbnail`}
                      className="h-24 w-40 rounded-md border border-slate-700 object-cover"
                    />
                  ) : (
                    <div className="h-24 w-40 rounded-md border border-slate-700 bg-slate-800/80" />
                  )}

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-3">
                      <h4 className="text-sm font-semibold text-white">{clip.title || `Clip ${index + 1}`}</h4>
                      <span className="rounded-full bg-purple-500/20 px-2.5 py-1 text-xs text-purple-200">
                        Score {(clip.score ?? 0).toFixed(2)}
                      </span>
                    </div>

                    <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-400">
                      <span>{formatClipDuration(clip.duration_sec)}</span>
                      <span>
                        {formatTimeBoundary(clip.start_time)} - {formatTimeBoundary(clip.end_time)}
                      </span>
                      <span>Hook {(clip.hook_score ?? 0).toFixed(2)}</span>
                      <span>Energy {(clip.energy_score ?? 0).toFixed(2)}</span>
                    </div>

                    <p className="mt-3 line-clamp-3 text-sm text-slate-300">
                      {clip.transcript_text || "Transcript excerpt unavailable."}
                    </p>

                    <div className="mt-4">
                      <Link
                        href={`/videos/${video.id}/clips/${clip.id}`}
                        className="inline-flex items-center rounded-md bg-[#7C3AED] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-[#6D28D9]"
                      >
                        Review & Export
                      </Link>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : null}

        {activeTab === "transcript" && video.status === "transcribing" ? (
          <div className="flex items-center gap-3 rounded-lg border border-slate-700 bg-slate-900/40 p-6 text-slate-200">
            <LoadingSpinner />
            <p>Transcribing your video... This takes about 6 minutes per hour of content</p>
          </div>
        ) : null}

        {activeTab === "transcript" && video.status === "error" ? (
          <div className="rounded-lg border border-red-900/60 bg-red-950/30 p-6 text-red-300">
            {video.error_message || "This video failed during processing."}
          </div>
        ) : null}

        {activeTab === "transcript" && (video.status === "scoring" || video.status === "ready") ? (
          transcript ? (
            <div className="space-y-4">
              <div className="flex flex-wrap gap-4 text-xs text-slate-400">
                <p>Words: {transcript.word_count}</p>
                <p>Language: {transcript.language || "Unknown"}</p>
              </div>
              <div className="max-h-[28rem] overflow-auto whitespace-pre-wrap rounded-lg border border-slate-700 bg-slate-900/40 p-4 text-sm leading-7 text-slate-200">
                {transcriptText || "Transcript text is empty."}
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-slate-700 bg-slate-900/40 p-6 text-slate-300">
              {transcriptError || "Transcript not ready yet"}
            </div>
          )
        ) : null}
      </Card>
    </div>
  );
}
