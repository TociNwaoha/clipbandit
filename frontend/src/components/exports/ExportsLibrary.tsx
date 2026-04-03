"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Card } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { api, ApiError } from "@/lib/api";
import { Export } from "@/types";

const ACTIVE_EXPORT_STATUSES = new Set(["queued", "rendering"]);

const statusStyles: Record<string, string> = {
  queued: "bg-slate-700/80 text-slate-200",
  rendering: "bg-blue-500/20 text-blue-300 animate-pulse",
  ready: "bg-emerald-500/20 text-emerald-300",
  error: "bg-red-500/20 text-red-300",
};

function statusLabel(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatRelativeTime(input: string): string {
  const now = Date.now();
  const then = new Date(input).getTime();
  const diffMs = then - now;
  const seconds = Math.round(diffMs / 1000);
  const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

  if (Math.abs(seconds) < 60) return rtf.format(seconds, "second");
  const minutes = Math.round(seconds / 60);
  if (Math.abs(minutes) < 60) return rtf.format(minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return rtf.format(hours, "hour");
  const days = Math.round(hours / 24);
  return rtf.format(days, "day");
}

function shortId(id: string): string {
  return id.slice(0, 8);
}

interface SelectionState {
  titleIndex: number;
  hashtagIndex: number;
}

interface ExportsLibraryProps {
  initialExports: Export[];
}

export function ExportsLibrary({ initialExports }: ExportsLibraryProps) {
  const [exports, setExports] = useState<Export[]>(initialExports);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryingExportId, setRetryingExportId] = useState<string | null>(null);
  const [copyMessageByExportId, setCopyMessageByExportId] = useState<Record<string, string>>({});
  const [selectionByExportId, setSelectionByExportId] = useState<Record<string, SelectionState>>({});

  const activeExports = useMemo(
    () => exports.some((item) => ACTIVE_EXPORT_STATUSES.has(item.status)),
    [exports]
  );

  const refreshExports = async () => {
    setLoading(true);
    setError(null);
    try {
      const latest = await api.get<Export[]>("/api/exports");
      setExports(latest);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load exports");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setSelectionByExportId((prev) => {
      const next = { ...prev };
      for (const item of exports) {
        if (!next[item.id]) {
          next[item.id] = { titleIndex: 0, hashtagIndex: 0 };
        }
      }
      return next;
    });
  }, [exports]);

  useEffect(() => {
    if (!activeExports) return;
    const timer = setInterval(() => {
      void refreshExports();
    }, 5000);
    return () => clearInterval(timer);
  }, [activeExports]);

  const setCopyMessage = (exportId: string, message: string) => {
    setCopyMessageByExportId((prev) => ({ ...prev, [exportId]: message }));
    window.setTimeout(() => {
      setCopyMessageByExportId((prev) => {
        const next = { ...prev };
        delete next[exportId];
        return next;
      });
    }, 2000);
  };

  const copyText = async (exportId: string, text: string, successLabel: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopyMessage(exportId, `${successLabel} copied`);
    } catch {
      setCopyMessage(exportId, "Clipboard copy failed");
    }
  };

  const retryExport = async (exportId: string) => {
    setRetryingExportId(exportId);
    setError(null);
    try {
      const created = await api.post<Export>(`/api/exports/${exportId}/retry`, {});
      setExports((prev) => [created, ...prev]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to retry export");
    } finally {
      setRetryingExportId(null);
    }
  };

  const setTitleIndex = (exportId: string, idx: number) => {
    setSelectionByExportId((prev) => ({
      ...prev,
      [exportId]: { ...(prev[exportId] || { titleIndex: 0, hashtagIndex: 0 }), titleIndex: idx },
    }));
  };

  const setHashtagIndex = (exportId: string, idx: number) => {
    setSelectionByExportId((prev) => ({
      ...prev,
      [exportId]: { ...(prev[exportId] || { titleIndex: 0, hashtagIndex: 0 }), hashtagIndex: idx },
    }));
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold text-white">Exports</h2>
          <p className="mt-1 text-sm text-slate-400">Download completed exports, retry failures, and copy social text.</p>
        </div>
        <button
          type="button"
          onClick={() => void refreshExports()}
          className="rounded-md border border-slate-700 px-3 py-2 text-sm text-slate-200 hover:bg-slate-800"
        >
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="inline-flex items-center gap-2 text-sm text-slate-400">
          <LoadingSpinner size="sm" />
          Refreshing exports...
        </div>
      ) : null}

      {error ? <p className="text-sm text-red-400">{error}</p> : null}

      {exports.length === 0 ? (
        <Card>
          <p className="text-sm text-slate-300">No exports yet.</p>
          <p className="mt-2 text-sm text-slate-400">
            Open a video clip and create an export to populate this library.
          </p>
        </Card>
      ) : null}

      {exports.map((item) => {
        const titles = item.clip_title_options || [];
        const hashtagSets = item.clip_hashtag_options || [];
        const copyReady =
          item.clip_copy_generation_status === "ready" &&
          titles.length >= 3 &&
          hashtagSets.length >= 3;
        const selection = selectionByExportId[item.id] || { titleIndex: 0, hashtagIndex: 0 };
        const selectedTitle = titles[selection.titleIndex] || titles[0] || "";
        const selectedHashtags = hashtagSets[selection.hashtagIndex] || hashtagSets[0] || [];
        const selectedHashtagsText = selectedHashtags.join(" ");
        const combinedCaption = selectedTitle
          ? `${selectedTitle}\n\n${selectedHashtagsText}`.trim()
          : selectedHashtagsText;

        return (
          <Card key={item.id}>
            <div className="flex flex-wrap gap-4">
              {item.clip_thumbnail_url ? (
                <img
                  src={item.clip_thumbnail_url}
                  alt="Clip thumbnail"
                  className="h-24 w-40 rounded-md border border-slate-700 object-cover"
                />
              ) : (
                <div className="h-24 w-40 rounded-md border border-slate-700 bg-slate-800/80" />
              )}

              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-white">
                      {item.video_title || "Untitled video"} • Export {shortId(item.id)}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      {item.clip_title || `Clip ${shortId(item.clip_id)}`} • {item.aspect_ratio} •{" "}
                      {item.caption_style || "no_style"} • {item.caption_format}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      Created {formatRelativeTime(item.created_at)}
                      {item.render_time_sec ? ` • Render ${item.render_time_sec}s` : ""}
                      {item.retry_of_export_id ? ` • Retry of ${shortId(item.retry_of_export_id)}` : ""}
                    </p>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                      statusStyles[item.status] || statusStyles.queued
                    }`}
                  >
                    {statusLabel(item.status)}
                  </span>
                </div>

                {item.error_message ? <p className="mt-3 text-sm text-red-400">{item.error_message}</p> : null}

                <div className="mt-3 flex flex-wrap items-center gap-4">
                  {item.status === "ready" && item.download_url ? (
                    <a
                      href={item.download_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-sm text-[#A78BFA] hover:text-[#C4B5FD]"
                    >
                      Download MP4
                    </a>
                  ) : null}
                  {item.status === "ready" && item.srt_download_url ? (
                    <a
                      href={item.srt_download_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-sm text-[#A78BFA] hover:text-[#C4B5FD]"
                    >
                      Download SRT
                    </a>
                  ) : null}
                  {item.video_id ? (
                    <Link
                      href={`/videos/${item.video_id}/clips/${item.clip_id}`}
                      className="text-sm text-slate-300 hover:text-white"
                    >
                      Open Clip
                    </Link>
                  ) : null}
                  {item.status === "error" ? (
                    <button
                      type="button"
                      disabled={retryingExportId === item.id}
                      onClick={() => void retryExport(item.id)}
                      className="rounded-md bg-[#7C3AED] px-3 py-1.5 text-xs font-medium text-white hover:bg-[#6D28D9] disabled:opacity-60"
                    >
                      {retryingExportId === item.id ? "Retrying..." : "Retry"}
                    </button>
                  ) : null}
                </div>

                <div className="mt-4 rounded-md border border-slate-700 bg-slate-900/30 p-3">
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-400">AI Copy</p>
                  {copyReady ? (
                    <div className="mt-3 space-y-3">
                      <div>
                        <p className="mb-2 text-xs text-slate-400">Title options</p>
                        <div className="flex flex-wrap gap-2">
                          {titles.map((title, idx) => (
                            <button
                              key={`${item.id}-title-${idx}`}
                              type="button"
                              onClick={() => setTitleIndex(item.id, idx)}
                              className={`rounded-md border px-2 py-1 text-xs ${
                                idx === selection.titleIndex
                                  ? "border-[#7C3AED] bg-[#7C3AED]/20 text-[#C4B5FD]"
                                  : "border-slate-700 text-slate-300 hover:bg-slate-800"
                              }`}
                            >
                              {title}
                            </button>
                          ))}
                        </div>
                      </div>

                      <div>
                        <p className="mb-2 text-xs text-slate-400">Hashtag sets</p>
                        <div className="flex flex-wrap gap-2">
                          {hashtagSets.map((tags, idx) => (
                            <button
                              key={`${item.id}-hashtags-${idx}`}
                              type="button"
                              onClick={() => setHashtagIndex(item.id, idx)}
                              className={`rounded-md border px-2 py-1 text-xs ${
                                idx === selection.hashtagIndex
                                  ? "border-[#7C3AED] bg-[#7C3AED]/20 text-[#C4B5FD]"
                                  : "border-slate-700 text-slate-300 hover:bg-slate-800"
                              }`}
                            >
                              {tags.join(" ")}
                            </button>
                          ))}
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => void copyText(item.id, selectedTitle, "Title")}
                          className="rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-200 hover:bg-slate-800"
                        >
                          Copy Title
                        </button>
                        <button
                          type="button"
                          onClick={() => void copyText(item.id, selectedHashtagsText, "Hashtags")}
                          className="rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-200 hover:bg-slate-800"
                        >
                          Copy Hashtags
                        </button>
                        <button
                          type="button"
                          onClick={() => void copyText(item.id, combinedCaption, "Video caption")}
                          className="rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-200 hover:bg-slate-800"
                        >
                          Copy Video Caption
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p className="mt-2 text-sm text-slate-300">
                      AI copy unavailable
                      {item.clip_copy_generation_error ? `: ${item.clip_copy_generation_error}` : ""}
                    </p>
                  )}

                  {copyMessageByExportId[item.id] ? (
                    <p className="mt-2 text-xs text-emerald-300">{copyMessageByExportId[item.id]}</p>
                  ) : null}
                </div>
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
