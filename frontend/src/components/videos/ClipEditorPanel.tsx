"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { Card } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { api, ApiError } from "@/lib/api";
import { AspectRatio, CaptionFormat, CaptionStyle, Clip, Export, Video } from "@/types";

interface ClipEditorPanelProps {
  video: Video;
  initialClip: Clip;
  initialExports: Export[];
}

const ACTIVE_EXPORT_STATUSES = new Set(["queued", "rendering"]);

const exportStatusStyles: Record<string, string> = {
  queued: "bg-slate-700/80 text-slate-200",
  rendering: "bg-blue-500/20 text-blue-300 animate-pulse",
  ready: "bg-emerald-500/20 text-emerald-300",
  error: "bg-red-500/20 text-red-300",
};

function formatTimeBoundary(seconds: number): string {
  const safe = Math.max(0, Math.floor(seconds));
  const mins = Math.floor(safe / 60);
  const secs = safe % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

function formatSeconds(seconds: number | null | undefined): string {
  const value = Number(seconds || 0);
  if (value <= 0) return "0.0s";
  return `${value.toFixed(1)}s`;
}

function statusLabel(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function parseNumberInput(value: string): number | null {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return null;
  return parsed;
}

export function ClipEditorPanel({ video, initialClip, initialExports }: ClipEditorPanelProps) {
  const [clip, setClip] = useState<Clip>(initialClip);
  const [clipStart, setClipStart] = useState<string>(initialClip.start_time.toFixed(2));
  const [clipEnd, setClipEnd] = useState<string>(initialClip.end_time.toFixed(2));
  const [saveLoading, setSaveLoading] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const [aspectRatio, setAspectRatio] = useState<AspectRatio>("9:16");
  const [captionStyle, setCaptionStyle] = useState<CaptionStyle>("bold_boxed");
  const [captionFormat, setCaptionFormat] = useState<CaptionFormat>("burned_in");
  const [exports, setExports] = useState<Export[]>(initialExports);
  const [exportsLoading, setExportsLoading] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [createExportLoading, setCreateExportLoading] = useState(false);
  const [createExportMessage, setCreateExportMessage] = useState<string | null>(null);

  const [mediaDuration, setMediaDuration] = useState<number | null>(video.duration_sec ?? null);
  const [previewError, setPreviewError] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const replayStopAtRef = useRef<number | null>(null);

  const sourceUrl = video.source_download_url || null;
  const activeExportExists = exports.some((item) => ACTIVE_EXPORT_STATUSES.has(item.status));

  const computedDuration = useMemo(() => {
    const start = parseNumberInput(clipStart);
    const end = parseNumberInput(clipEnd);
    if (start === null || end === null) return null;
    const duration = end - start;
    if (duration <= 0) return null;
    return duration;
  }, [clipStart, clipEnd]);

  const refreshExports = async () => {
    setExportsLoading(true);
    setExportError(null);
    try {
      const items = await api.get<Export[]>(`/api/exports?clip_id=${encodeURIComponent(clip.id)}`);
      setExports(items);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Failed to load exports";
      setExportError(message);
    } finally {
      setExportsLoading(false);
    }
  };

  useEffect(() => {
    if (!activeExportExists) return;
    const timer = setInterval(() => {
      void refreshExports();
    }, 5000);
    return () => clearInterval(timer);
  }, [activeExportExists, clip.id]);

  const handleReplay = async () => {
    const player = videoRef.current;
    if (!player) return;

    const start = parseNumberInput(clipStart);
    const end = parseNumberInput(clipEnd);
    if (start === null || end === null || end <= start) return;

    replayStopAtRef.current = end;
    player.currentTime = start;
    await player.play().catch(() => undefined);
  };

  const handleSeekStart = () => {
    const player = videoRef.current;
    if (!player) return;
    const start = parseNumberInput(clipStart);
    if (start === null) return;
    player.currentTime = Math.max(start, 0);
  };

  const handleTimeUpdate = () => {
    const player = videoRef.current;
    if (!player) return;
    const stopAt = replayStopAtRef.current;
    if (stopAt === null) return;
    if (player.currentTime >= stopAt) {
      player.pause();
      const start = parseNumberInput(clipStart);
      if (start !== null) player.currentTime = Math.max(start, 0);
      replayStopAtRef.current = null;
    }
  };

  const handleSaveTrim = async () => {
    setSaveError(null);
    setSaveMessage(null);

    const start = parseNumberInput(clipStart);
    const end = parseNumberInput(clipEnd);
    if (start === null || end === null) {
      setSaveError("Start and end must be valid numbers.");
      return;
    }

    let nextStart = Math.max(start, 0);
    let nextEnd = Math.max(end, 0);
    const maxDuration = mediaDuration ?? video.duration_sec ?? null;
    if (maxDuration && maxDuration > 0) {
      nextStart = Math.min(nextStart, maxDuration);
      nextEnd = Math.min(nextEnd, maxDuration);
    }

    if (nextEnd <= nextStart) {
      setSaveError("End time must be greater than start time.");
      return;
    }

    setSaveLoading(true);
    try {
      const updated = await api.patch<Clip>(`/api/clips/${clip.id}`, {
        video_id: video.id,
        start_time: nextStart,
        end_time: nextEnd,
      });
      setClip(updated);
      setClipStart(updated.start_time.toFixed(2));
      setClipEnd(updated.end_time.toFixed(2));
      setSaveMessage("Trim updated.");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Failed to save trim changes";
      setSaveError(message);
    } finally {
      setSaveLoading(false);
    }
  };

  const handleCreateExport = async () => {
    setCreateExportLoading(true);
    setCreateExportMessage(null);
    setExportError(null);
    try {
      const created = await api.post<Export>("/api/exports", {
        clip_id: clip.id,
        aspect_ratio: aspectRatio,
        caption_style: captionStyle,
        caption_format: captionFormat,
      });
      setExports((prev) => {
        const existingIndex = prev.findIndex((item) => item.id === created.id);
        if (existingIndex >= 0) {
          const next = [...prev];
          next[existingIndex] = created;
          return next;
        }
        return [created, ...prev];
      });
      if (created.reused) {
        setCreateExportMessage("Identical export is already in progress. Reusing existing export.");
      } else {
        setCreateExportMessage("Export created and queued.");
      }
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Failed to create export";
      setExportError(message);
    } finally {
      setCreateExportLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">Clip Editor</p>
            <h2 className="mt-1 text-xl font-semibold text-white">{clip.title || "Untitled clip"}</h2>
            <p className="mt-1 text-sm text-slate-400">
              Video: {video.title || "Untitled video"} • Clip {formatTimeBoundary(clip.start_time)} -{" "}
              {formatTimeBoundary(clip.end_time)}
            </p>
          </div>
          <Link
            href={`/videos/${video.id}`}
            className="rounded-md border border-slate-700 px-3 py-2 text-sm text-slate-200 hover:bg-slate-800"
          >
            Back to Video
          </Link>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <Card>
          <h3 className="text-sm font-semibold text-white">Preview</h3>
          <p className="mt-1 text-xs text-slate-400">
            Source preview with current clip boundaries. Replay starts from the selected start time.
          </p>
          <div className="mt-4 overflow-hidden rounded-lg border border-slate-700 bg-black">
            {sourceUrl ? (
              <video
                ref={videoRef}
                controls
                src={sourceUrl}
                className="h-[320px] w-full bg-black object-contain"
                onLoadedMetadata={(event) => {
                  const duration = event.currentTarget.duration;
                  if (Number.isFinite(duration) && duration > 0) {
                    setMediaDuration(duration);
                  }
                }}
                onError={() => setPreviewError("Preview failed to load source video.")}
                onTimeUpdate={handleTimeUpdate}
              />
            ) : (
              <div className="flex h-[320px] items-center justify-center text-sm text-slate-400">
                Source preview URL is unavailable for this video.
              </div>
            )}
          </div>
          {previewError ? <p className="mt-2 text-sm text-red-400">{previewError}</p> : null}

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => void handleReplay()}
              className="rounded-md bg-[#7C3AED] px-3 py-2 text-sm font-medium text-white hover:bg-[#6D28D9]"
            >
              Replay Clip
            </button>
            <button
              type="button"
              onClick={handleSeekStart}
              className="rounded-md border border-slate-700 px-3 py-2 text-sm text-slate-200 hover:bg-slate-800"
            >
              Seek to Start
            </button>
            <span className="text-xs text-slate-400">
              Clip range: {clipStart}s - {clipEnd}s ({formatSeconds(computedDuration)})
            </span>
          </div>
        </Card>

        <Card>
          <h3 className="text-sm font-semibold text-white">Trim</h3>
          {clip.thumbnail_url ? (
            <img
              src={clip.thumbnail_url}
              alt="Clip thumbnail"
              className="mt-4 h-32 w-full rounded-md border border-slate-700 object-cover"
            />
          ) : null}
          <div className="mt-4 space-y-3">
            <label className="block text-xs text-slate-400">
              Start (seconds)
              <input
                type="number"
                step="0.1"
                min={0}
                value={clipStart}
                onChange={(event) => setClipStart(event.target.value)}
                className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:border-[#7C3AED] focus:outline-none"
              />
            </label>
            <label className="block text-xs text-slate-400">
              End (seconds)
              <input
                type="number"
                step="0.1"
                min={0}
                value={clipEnd}
                onChange={(event) => setClipEnd(event.target.value)}
                className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:border-[#7C3AED] focus:outline-none"
              />
            </label>
            <p className="text-xs text-slate-400">
              Duration: <span className="text-slate-200">{formatSeconds(computedDuration)}</span>
              {mediaDuration ? (
                <>
                  {" "}
                  • Video length: <span className="text-slate-200">{formatSeconds(mediaDuration)}</span>
                </>
              ) : null}
            </p>
            <button
              type="button"
              onClick={() => void handleSaveTrim()}
              disabled={saveLoading}
              className="w-full rounded-md bg-[#7C3AED] px-3 py-2 text-sm font-medium text-white hover:bg-[#6D28D9] disabled:opacity-60"
            >
              {saveLoading ? "Saving..." : "Save Trim"}
            </button>
            {saveMessage ? <p className="text-xs text-emerald-300">{saveMessage}</p> : null}
            {saveError ? <p className="text-xs text-red-400">{saveError}</p> : null}
          </div>
        </Card>
      </div>

      <Card>
        <h3 className="text-sm font-semibold text-white">Transcript Context</h3>
        <p className="mt-3 max-h-40 overflow-y-auto whitespace-pre-wrap rounded-md border border-slate-700 bg-slate-900/40 p-3 text-sm text-slate-300">
          {clip.transcript_text || "Transcript excerpt unavailable for this clip."}
        </p>
      </Card>

      <Card>
        <h3 className="text-sm font-semibold text-white">Export Settings</h3>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          <label className="text-xs text-slate-400">
            Caption Style
            <select
              value={captionStyle}
              onChange={(event) => setCaptionStyle(event.target.value as CaptionStyle)}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:border-[#7C3AED] focus:outline-none"
            >
              <option value="bold_boxed">bold_boxed</option>
              <option value="sermon_quote">sermon_quote</option>
              <option value="clean_minimal">clean_minimal</option>
            </select>
          </label>
          <label className="text-xs text-slate-400">
            Aspect Ratio
            <select
              value={aspectRatio}
              onChange={(event) => setAspectRatio(event.target.value as AspectRatio)}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:border-[#7C3AED] focus:outline-none"
            >
              <option value="9:16">9:16</option>
              <option value="1:1">1:1</option>
            </select>
          </label>
          <label className="text-xs text-slate-400">
            Caption Format
            <select
              value={captionFormat}
              onChange={(event) => setCaptionFormat(event.target.value as CaptionFormat)}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:border-[#7C3AED] focus:outline-none"
            >
              <option value="burned_in">burned_in</option>
              <option value="srt">srt</option>
            </select>
          </label>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => void handleCreateExport()}
            disabled={createExportLoading}
            className="rounded-md bg-[#7C3AED] px-4 py-2 text-sm font-medium text-white hover:bg-[#6D28D9] disabled:opacity-60"
          >
            {createExportLoading ? "Creating Export..." : "Create Export"}
          </button>
          {createExportMessage ? <p className="text-sm text-emerald-300">{createExportMessage}</p> : null}
        </div>
      </Card>

      <Card>
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white">Export History</h3>
          {exportsLoading ? (
            <span className="inline-flex items-center gap-2 text-xs text-slate-400">
              <LoadingSpinner />
              Refreshing...
            </span>
          ) : null}
        </div>
        {exportError ? <p className="mt-3 text-sm text-red-400">{exportError}</p> : null}

        {!exports.length && !exportsLoading ? (
          <p className="mt-4 rounded-md border border-slate-700 bg-slate-900/40 p-4 text-sm text-slate-400">
            No exports yet for this clip.
          </p>
        ) : null}

        {exports.length ? (
          <div className="mt-4 space-y-3">
            {exports.map((item) => (
              <div key={item.id} className="rounded-md border border-slate-700 bg-slate-900/40 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="text-sm text-slate-200">
                    <p className="font-medium">Export {item.id.slice(0, 8)}</p>
                    <p className="mt-1 text-xs text-slate-400">
                      {item.aspect_ratio} • {item.caption_style || "no_style"} • {item.caption_format}
                    </p>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                      exportStatusStyles[item.status] || exportStatusStyles.queued
                    }`}
                  >
                    {statusLabel(item.status)}
                  </span>
                </div>
                {item.error_message ? <p className="mt-3 text-xs text-red-400">{item.error_message}</p> : null}
                {item.status === "ready" && item.download_url ? (
                  <div className="mt-3 flex flex-wrap items-center gap-4">
                    <a
                      href={item.download_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex text-xs text-[#A78BFA] hover:text-[#C4B5FD]"
                    >
                      Download export
                    </a>
                    {item.srt_download_url ? (
                      <a
                        href={item.srt_download_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex text-xs text-[#A78BFA] hover:text-[#C4B5FD]"
                      >
                        Download captions (.srt)
                      </a>
                    ) : null}
                  </div>
                ) : null}
                {item.status === "ready" && !item.download_url ? (
                  <p className="mt-3 text-xs text-slate-400">Export is ready but no download URL is available yet.</p>
                ) : null}
              </div>
            ))}
          </div>
        ) : null}
      </Card>
    </div>
  );
}
