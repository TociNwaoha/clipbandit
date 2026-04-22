"use client";

import { Card } from "@/components/ui/Card";
import { PlaylistImport } from "@/types";

interface PlaylistImportCardProps {
  playlist: PlaylistImport;
}

const statusStyles: Record<string, string> = {
  queued: "bg-slate-700/80 text-slate-200",
  expanding: "bg-blue-500/20 text-blue-300 animate-pulse",
  importing: "bg-blue-500/20 text-blue-300 animate-pulse",
  completed: "bg-emerald-500/20 text-emerald-300",
  partial: "bg-amber-500/20 text-amber-300",
  failed: "bg-red-500/20 text-red-300",
};

function statusLabel(status: string): string {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function importStateLabel(state: string | null): string {
  if (!state) return "Unknown";
  return state
    .split(":")[0]
    .split("_")
    .filter(Boolean)
    .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))
    .join(" ");
}

export function PlaylistImportCard({ playlist }: PlaylistImportCardProps) {
  const total = Math.max(playlist.total_items, playlist.items.length);
  const done = Math.min(playlist.completed_items, total || playlist.completed_items);
  const progress = total > 0 ? Math.round((done / total) * 100) : 0;

  return (
    <Card>
      <div className="space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-white">
              {playlist.title || `Playlist ${playlist.playlist_id}`}
            </p>
            <p className="mt-1 truncate text-xs text-slate-400">{playlist.source_url}</p>
          </div>
          <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusStyles[playlist.status] || statusStyles.queued}`}>
            {statusLabel(playlist.status)}
          </span>
        </div>

        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Playlist import</span>
            <span>
              {done}/{total || 0}
            </span>
          </div>
          <div className="h-2 rounded-full bg-slate-800">
            <div className="h-2 rounded-full bg-[#7C3AED]" style={{ width: `${progress}%` }} />
          </div>
        </div>

        {playlist.items.length > 0 ? (
          <div className="max-h-48 space-y-2 overflow-auto pr-1">
            {playlist.items.map((item) => (
              <div key={item.id} className="rounded-md border border-slate-700 bg-slate-900/50 px-3 py-2">
                <div className="flex items-start justify-between gap-2">
                  <p className="truncate text-xs text-slate-200">
                    {(item.playlist_index ?? 0) + 1}. {item.title || item.source_video_id || "Unknown video"}
                  </p>
                  <span className="text-[10px] uppercase text-slate-400">
                    {item.import_state === "processing" ? item.status : importStateLabel(item.import_state)}
                  </span>
                </div>
                {item.is_download_blocked ? (
                  <div className="mt-1 flex flex-wrap gap-1">
                    <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[10px] text-amber-300">
                      Blocked on server
                    </span>
                    <span className="rounded bg-blue-500/20 px-1.5 py-0.5 text-[10px] text-blue-300">
                      Can still embed
                    </span>
                    <span className="rounded bg-slate-700 px-1.5 py-0.5 text-[10px] text-slate-200">
                      Upload file manually
                    </span>
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </Card>
  );
}
