"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { Card } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { api, ApiError } from "@/lib/api";
import {
  buildCaptionPreviewText,
  getCaptionPreviewLayout,
  getCaptionStyleTheme,
  wrapCaptionPreviewText,
} from "@/lib/captionPreview";
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

function formatClockTime(seconds: number | null | undefined): string {
  const safeValue = Number(seconds || 0);
  if (!Number.isFinite(safeValue) || safeValue <= 0) return "0:00";
  const whole = Math.floor(safeValue);
  const hours = Math.floor(whole / 3600);
  const minutes = Math.floor((whole % 3600) / 60);
  const secs = whole % 60;
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }
  return `${minutes}:${secs.toString().padStart(2, "0")}`;
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
  const [playerCurrentTime, setPlayerCurrentTime] = useState<number>(0);
  const [previewError, setPreviewError] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const replayStopAtRef = useRef<number | null>(null);
  const replayActiveRef = useRef<boolean>(false);

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

  const normalizedMediaDuration = useMemo(() => {
    const duration = Number(mediaDuration ?? video.duration_sec ?? 0);
    if (!Number.isFinite(duration) || duration <= 0) return null;
    return duration;
  }, [mediaDuration, video.duration_sec]);

  const normalizedClipRange = useMemo(() => {
    const start = parseNumberInput(clipStart);
    const end = parseNumberInput(clipEnd);
    if (start === null || end === null) return null;

    let safeStart = Math.max(0, start);
    let safeEnd = Math.max(0, end);
    if (normalizedMediaDuration) {
      safeStart = Math.min(safeStart, normalizedMediaDuration);
      safeEnd = Math.min(safeEnd, normalizedMediaDuration);
    }
    if (safeEnd <= safeStart) return null;

    return {
      start: safeStart,
      end: safeEnd,
      duration: safeEnd - safeStart,
    };
  }, [clipStart, clipEnd, normalizedMediaDuration]);

  const timelineMetrics = useMemo(() => {
    if (!normalizedMediaDuration || !normalizedClipRange) return null;
    const toPercent = (value: number) =>
      Math.min(100, Math.max(0, (value / normalizedMediaDuration) * 100));

    const clipStartPercent = toPercent(normalizedClipRange.start);
    const clipEndPercent = toPercent(normalizedClipRange.end);
    const clipWidthPercent = Math.max(0, clipEndPercent - clipStartPercent);
    const playheadPercent = toPercent(playerCurrentTime);

    return {
      clipStartPercent,
      clipEndPercent,
      clipWidthPercent,
      playheadPercent,
    };
  }, [normalizedMediaDuration, normalizedClipRange, playerCurrentTime]);

  const previewAspectRatioValue = aspectRatio === "9:16" ? "9 / 16" : "1 / 1";
  const previewMaxWidthClass = aspectRatio === "9:16" ? "max-w-[360px]" : "max-w-[480px]";

  const captionPreviewLayout = useMemo(
    () => getCaptionPreviewLayout(captionStyle, aspectRatio),
    [captionStyle, aspectRatio]
  );
  const captionPreviewTheme = useMemo(() => getCaptionStyleTheme(captionStyle), [captionStyle]);
  const captionPreviewText = useMemo(
    () => buildCaptionPreviewText(clip.transcript_text),
    [clip.transcript_text]
  );
  const captionPreviewLines = useMemo(
    () =>
      wrapCaptionPreviewText(
        captionPreviewText,
        captionPreviewLayout.maxCharsPerLine,
        captionPreviewLayout.maxLines
      ),
    [captionPreviewLayout.maxCharsPerLine, captionPreviewLayout.maxLines, captionPreviewText]
  );

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

    if (!normalizedClipRange) return;
    player.pause();
    player.currentTime = normalizedClipRange.start;
    setPlayerCurrentTime(normalizedClipRange.start);
    replayStopAtRef.current = normalizedClipRange.end;
    replayActiveRef.current = true;

    await player.play().catch(() => {
      replayActiveRef.current = false;
      replayStopAtRef.current = null;
    });
  };

  const handleSeekStart = () => {
    const player = videoRef.current;
    if (!player) return;
    if (!normalizedClipRange) return;
    player.currentTime = normalizedClipRange.start;
    setPlayerCurrentTime(normalizedClipRange.start);
  };

  const handleTimeUpdate = () => {
    const player = videoRef.current;
    if (!player) return;
    setPlayerCurrentTime(player.currentTime);

    if (!replayActiveRef.current) return;
    const stopAt = replayStopAtRef.current;
    if (stopAt === null) return;
    if (player.currentTime >= stopAt - 0.03) {
      player.pause();
      player.currentTime = stopAt;
      setPlayerCurrentTime(stopAt);
      replayActiveRef.current = false;
      replayStopAtRef.current = null;
    }
  };

  const handleSeeked = () => {
    const player = videoRef.current;
    if (!player) return;
    setPlayerCurrentTime(player.currentTime);
    const stopAt = replayStopAtRef.current;
    if (replayActiveRef.current && stopAt !== null && player.currentTime > stopAt) {
      player.pause();
      player.currentTime = stopAt;
      setPlayerCurrentTime(stopAt);
      replayActiveRef.current = false;
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
            Source preview with current clip boundaries and caption style preview for selected export settings.
          </p>
          <div className={`relative mx-auto mt-4 w-full ${previewMaxWidthClass}`}>
            <div className="mb-2 flex items-center justify-between text-xs text-slate-400">
              <span>Preview Frame</span>
              <span>
                {aspectRatio} • {captionStyle} • {captionFormat}
              </span>
            </div>
            <div
              className="relative overflow-hidden rounded-lg border border-slate-700 bg-black"
              style={{ aspectRatio: previewAspectRatioValue }}
            >
            {sourceUrl ? (
              <video
                ref={videoRef}
                controls
                src={sourceUrl}
                className="h-full w-full bg-black object-cover"
                onLoadedMetadata={(event) => {
                  const duration = event.currentTarget.duration;
                  if (Number.isFinite(duration) && duration > 0) {
                    setMediaDuration(duration);
                  }
                  setPlayerCurrentTime(event.currentTarget.currentTime || 0);
                }}
                onError={() => setPreviewError("Preview failed to load source video.")}
                onTimeUpdate={handleTimeUpdate}
                onSeeked={handleSeeked}
              />
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-slate-400">
                Source preview URL is unavailable for this video.
              </div>
            )}

            <div className="pointer-events-none absolute inset-0 z-20 flex items-end justify-center">
              <div
                className="w-full"
                style={{
                  paddingLeft: `${captionPreviewLayout.marginXPercent}%`,
                  paddingRight: `${captionPreviewLayout.marginXPercent}%`,
                  paddingBottom: `${captionPreviewLayout.marginBottomPercent}%`,
                }}
              >
                <div
                  className="mx-auto w-full text-center text-white"
                  style={{
                    fontSize: `${captionPreviewLayout.fontSizePx}px`,
                    lineHeight: captionPreviewLayout.lineHeight,
                    fontWeight: captionPreviewTheme.bold ? 700 : 500,
                    fontStyle: captionPreviewTheme.italic ? "italic" : "normal",
                    textShadow:
                      captionPreviewTheme.outlinePx > 0
                        ? `0 0 ${captionPreviewTheme.outlinePx}px rgba(0,0,0,0.9), 0 2px ${
                            captionPreviewTheme.outlinePx + 1
                          }px rgba(0,0,0,0.75)`
                        : "0 1px 2px rgba(0,0,0,0.75)",
                    padding: captionPreviewTheme.boxed ? "6px 10px" : "0",
                    borderRadius: captionPreviewTheme.boxed ? "8px" : "0",
                    backgroundColor: `rgba(0,0,0,${captionPreviewTheme.backgroundOpacity})`,
                  }}
                >
                  {captionPreviewLines.map((line, index) => (
                    <div key={`caption-preview-line-${index}`}>{line}</div>
                  ))}
                </div>
              </div>
            </div>

            <div className="pointer-events-none absolute right-2 top-2 z-20 rounded-md bg-black/65 px-2 py-1 text-[11px] text-slate-200">
              {captionFormat === "burned_in" ? "Burned-in caption preview" : "SRT style preview"}
            </div>
            </div>
          </div>
          {previewError ? <p className="mt-2 text-sm text-red-400">{previewError}</p> : null}

          <div className="mt-4 rounded-lg border border-slate-700 bg-slate-900/40 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
              <span>Source Timeline</span>
              <span>
                Playhead {formatClockTime(playerCurrentTime)} / {formatClockTime(normalizedMediaDuration)}
              </span>
            </div>

            {timelineMetrics ? (
              <>
                <div className="relative mt-3 h-5">
                  <div className="absolute inset-x-0 top-1/2 h-2 -translate-y-1/2 rounded-full bg-slate-800" />
                  <div
                    className="absolute top-1/2 h-2 -translate-y-1/2 rounded-full border border-[#A78BFA] bg-[#7C3AED]/45"
                    style={{
                      left: `${timelineMetrics.clipStartPercent}%`,
                      width: `${timelineMetrics.clipWidthPercent}%`,
                    }}
                  />

                  <div
                    className="absolute top-0 h-5 w-0.5 bg-[#C4B5FD]"
                    style={{ left: `${timelineMetrics.clipStartPercent}%` }}
                  />
                  <div
                    className="absolute top-0 h-5 w-0.5 bg-[#C4B5FD]"
                    style={{ left: `${timelineMetrics.clipEndPercent}%` }}
                  />

                  <div
                    className="absolute top-0 h-5 w-0.5 bg-sky-300"
                    style={{ left: `${timelineMetrics.playheadPercent}%` }}
                  >
                    <div className="absolute -left-1 -top-1 h-2 w-2 rounded-full bg-sky-300" />
                  </div>
                </div>
                <div className="mt-1 flex items-center justify-between text-[11px] text-slate-500">
                  <span>0:00</span>
                  <span>{formatClockTime(normalizedMediaDuration)}</span>
                </div>
              </>
            ) : (
              <p className="mt-2 text-xs text-slate-500">
                Timeline becomes active after valid clip timings and video metadata are available.
              </p>
            )}

            <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
              <div className="rounded-md border border-slate-700 bg-slate-950/60 px-3 py-2">
                <p className="text-[11px] uppercase tracking-wide text-slate-400">Clip Start</p>
                <p className="text-sm font-semibold text-white">
                  {formatClockTime(normalizedClipRange?.start ?? parseNumberInput(clipStart) ?? 0)}
                </p>
              </div>
              <div className="rounded-md border border-slate-700 bg-slate-950/60 px-3 py-2">
                <p className="text-[11px] uppercase tracking-wide text-slate-400">Clip End</p>
                <p className="text-sm font-semibold text-white">
                  {formatClockTime(normalizedClipRange?.end ?? parseNumberInput(clipEnd) ?? 0)}
                </p>
              </div>
              <div className="rounded-md border border-[#7C3AED]/50 bg-[#7C3AED]/10 px-3 py-2">
                <p className="text-[11px] uppercase tracking-wide text-[#C4B5FD]">Clip Duration</p>
                <p className="text-base font-semibold text-white">{formatSeconds(normalizedClipRange?.duration ?? computedDuration)}</p>
              </div>
            </div>
          </div>

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
              Jump to Clip Start
            </button>
            <span className="text-xs text-slate-400">
              Clip range: {formatClockTime(normalizedClipRange?.start ?? parseNumberInput(clipStart) ?? 0)} -{" "}
              {formatClockTime(normalizedClipRange?.end ?? parseNumberInput(clipEnd) ?? 0)} (
              {formatSeconds(normalizedClipRange?.duration ?? computedDuration)})
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
