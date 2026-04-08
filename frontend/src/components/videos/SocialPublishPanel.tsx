"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { api, ApiError } from "@/lib/api";
import {
  ConnectedAccount,
  Export,
  PublishJobStatus,
  SocialPlatform,
  SocialProvider,
  SocialPublishJob,
} from "@/types";

interface SocialPublishPanelProps {
  exports: Export[];
}

interface PublishFormFields {
  caption: string;
  title: string;
  description: string;
  hashtags: string;
  privacy: string;
  scheduled_for: string;
}

interface TargetDraft {
  enabled: boolean;
  connected_account_id: string;
  use_override: boolean;
  override: PublishFormFields;
}

const PLATFORM_ORDER: SocialPlatform[] = ["instagram", "tiktok", "facebook", "youtube", "x", "linkedin"];
const ACTIVE_PUBLISH_STATUSES = new Set<PublishJobStatus>(["queued", "publishing"]);

const statusStyles: Record<PublishJobStatus, string> = {
  queued: "bg-slate-700/80 text-slate-200",
  publishing: "bg-blue-500/20 text-blue-300 animate-pulse",
  published: "bg-emerald-500/20 text-emerald-300",
  failed: "bg-red-500/20 text-red-300",
  waiting_user_action: "bg-amber-500/20 text-amber-300",
  provider_not_configured: "bg-yellow-500/20 text-yellow-300",
};

function emptyFields(): PublishFormFields {
  return {
    caption: "",
    title: "",
    description: "",
    hashtags: "",
    privacy: "",
    scheduled_for: "",
  };
}

function normalizeText(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length ? trimmed : null;
}

function parseHashtags(value: string): string[] | null {
  const parts = value
    .split(/[,\s]+/)
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => (item.startsWith("#") ? item : `#${item}`));

  const deduped: string[] = [];
  const seen = new Set<string>();
  for (const item of parts) {
    const key = item.toLowerCase();
    if (!seen.has(key)) {
      seen.add(key);
      deduped.push(item);
    }
  }
  return deduped.length ? deduped : null;
}

function toIsoDatetime(value: string): string | null {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toISOString();
}

function toPayloadFields(fields: PublishFormFields) {
  return {
    caption: normalizeText(fields.caption),
    title: normalizeText(fields.title),
    description: normalizeText(fields.description),
    hashtags: parseHashtags(fields.hashtags),
    privacy: normalizeText(fields.privacy),
    scheduled_for: toIsoDatetime(fields.scheduled_for),
  };
}

function prettyStatus(status: PublishJobStatus): string {
  return status
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function hasAnyOverrideValue(fields: PublishFormFields): boolean {
  return Boolean(
    fields.caption.trim() ||
      fields.title.trim() ||
      fields.description.trim() ||
      fields.hashtags.trim() ||
      fields.privacy.trim() ||
      fields.scheduled_for.trim()
  );
}

export function SocialPublishPanel({ exports }: SocialPublishPanelProps) {
  const readyExports = useMemo(
    () => exports.filter((item) => item.status === "ready" && item.storage_key),
    [exports]
  );
  const [selectedExportId, setSelectedExportId] = useState<string>("");
  const [providers, setProviders] = useState<SocialProvider[]>([]);
  const [accounts, setAccounts] = useState<ConnectedAccount[]>([]);
  const [publishJobs, setPublishJobs] = useState<SocialPublishJob[]>([]);
  const [universalFields, setUniversalFields] = useState<PublishFormFields>(emptyFields());
  const [targetDrafts, setTargetDrafts] = useState<Record<SocialPlatform, TargetDraft>>(
    Object.fromEntries(
      PLATFORM_ORDER.map((platform) => [platform, { enabled: false, connected_account_id: "", use_override: false, override: emptyFields() }])
    ) as Record<SocialPlatform, TargetDraft>
  );
  const [loadingMeta, setLoadingMeta] = useState(true);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [retryingJobId, setRetryingJobId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!readyExports.length) {
      setSelectedExportId("");
      return;
    }
    if (!selectedExportId || !readyExports.some((item) => item.id === selectedExportId)) {
      setSelectedExportId(readyExports[0].id);
    }
  }, [readyExports, selectedExportId]);

  const providersByPlatform = useMemo(
    () => Object.fromEntries(providers.map((provider) => [provider.platform, provider])) as Record<string, SocialProvider>,
    [providers]
  );

  const accountsByPlatform = useMemo(() => {
    const grouped: Record<string, ConnectedAccount[]> = {};
    for (const account of accounts) {
      if (!grouped[account.platform]) {
        grouped[account.platform] = [];
      }
      grouped[account.platform].push(account);
    }
    return grouped;
  }, [accounts]);

  const latestJobsByPlatform = useMemo(() => {
    const map = new Map<SocialPlatform, SocialPublishJob>();
    for (const job of publishJobs) {
      if (!map.has(job.platform)) {
        map.set(job.platform, job);
      }
    }
    return map;
  }, [publishJobs]);

  const loadMeta = async () => {
    setLoadingMeta(true);
    setError(null);
    try {
      const [providersData, accountsData] = await Promise.all([
        api.get<SocialProvider[]>("/api/social/providers"),
        api.get<ConnectedAccount[]>("/api/social/accounts"),
      ]);
      setProviders(providersData);
      setAccounts(accountsData);

      setTargetDrafts((previous) => {
        const next = { ...previous };
        for (const platform of PLATFORM_ORDER) {
          const platformAccounts = accountsData.filter((account) => account.platform === platform);
          const defaultAccountId = platformAccounts[0]?.id ?? "";
          const prior = previous[platform] ?? {
            enabled: false,
            connected_account_id: "",
            use_override: false,
            override: emptyFields(),
          };

          next[platform] = {
            ...prior,
            connected_account_id:
              prior.connected_account_id && platformAccounts.some((account) => account.id === prior.connected_account_id)
                ? prior.connected_account_id
                : defaultAccountId,
          };
        }
        return next;
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load social providers");
    } finally {
      setLoadingMeta(false);
    }
  };

  const loadPublishJobs = async (exportId: string) => {
    if (!exportId) {
      setPublishJobs([]);
      return;
    }
    setLoadingJobs(true);
    try {
      const jobs = await api.get<SocialPublishJob[]>(
        `/api/social/publish?export_id=${encodeURIComponent(exportId)}`
      );
      setPublishJobs(jobs);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load publish status");
    } finally {
      setLoadingJobs(false);
    }
  };

  useEffect(() => {
    void loadMeta();
  }, []);

  useEffect(() => {
    void loadPublishJobs(selectedExportId);
  }, [selectedExportId]);

  useEffect(() => {
    if (!publishJobs.some((job) => ACTIVE_PUBLISH_STATUSES.has(job.status))) return;
    const timer = window.setInterval(() => {
      if (!selectedExportId) return;
      void loadPublishJobs(selectedExportId);
    }, 5000);
    return () => window.clearInterval(timer);
  }, [publishJobs, selectedExportId]);

  const handlePlatformToggle = (platform: SocialPlatform, enabled: boolean) => {
    setTargetDrafts((previous) => ({
      ...previous,
      [platform]: {
        ...previous[platform],
        enabled,
      },
    }));
  };

  const handlePlatformAccountChange = (platform: SocialPlatform, accountId: string) => {
    setTargetDrafts((previous) => ({
      ...previous,
      [platform]: {
        ...previous[platform],
        connected_account_id: accountId,
      },
    }));
  };

  const handleOverrideToggle = (platform: SocialPlatform, useOverride: boolean) => {
    setTargetDrafts((previous) => ({
      ...previous,
      [platform]: {
        ...previous[platform],
        use_override: useOverride,
      },
    }));
  };

  const handleOverrideFieldChange = (
    platform: SocialPlatform,
    key: keyof PublishFormFields,
    value: string
  ) => {
    setTargetDrafts((previous) => ({
      ...previous,
      [platform]: {
        ...previous[platform],
        override: {
          ...previous[platform].override,
          [key]: value,
        },
      },
    }));
  };

  const handleCreatePublishJobs = async () => {
    if (!selectedExportId) {
      setError("Select a ready export before publishing.");
      return;
    }

    const targets = PLATFORM_ORDER.flatMap((platform) => {
      const draft = targetDrafts[platform];
      if (!draft?.enabled || !draft.connected_account_id) return [];

      const target: Record<string, unknown> = {
        platform,
        connected_account_id: draft.connected_account_id,
      };
      if (draft.use_override && hasAnyOverrideValue(draft.override)) {
        target.override = toPayloadFields(draft.override);
      }
      return [target];
    });

    if (!targets.length) {
      setError("Select at least one platform and connected account.");
      return;
    }

    setPublishing(true);
    setError(null);
    setMessage(null);
    try {
      const created = await api.post<SocialPublishJob[]>("/api/social/publish", {
        export_id: selectedExportId,
        universal: toPayloadFields(universalFields),
        targets,
      });
      setMessage(`Created ${created.length} publish job(s).`);
      await loadPublishJobs(selectedExportId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create publish jobs");
    } finally {
      setPublishing(false);
    }
  };

  const handleRetry = async (publishJobId: string) => {
    setRetryingJobId(publishJobId);
    setError(null);
    setMessage(null);
    try {
      await api.post<SocialPublishJob>(`/api/social/publish/${publishJobId}/retry`, {});
      setMessage("Retry queued.");
      await loadPublishJobs(selectedExportId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to retry publish job");
    } finally {
      setRetryingJobId(null);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-white">Publish to Social</h3>
          <p className="mt-1 text-xs text-slate-400">
            Publish from a ready export. One publish job is created per selected platform/account.
          </p>
        </div>
        <Link href="/connections" className="text-xs text-[#A78BFA] hover:text-[#C4B5FD]">
          Manage Connections
        </Link>
      </div>

      {message ? <p className="text-sm text-emerald-300">{message}</p> : null}
      {error ? <p className="text-sm text-red-400">{error}</p> : null}

      {loadingMeta ? (
        <p className="inline-flex items-center gap-2 text-sm text-slate-300">
          <LoadingSpinner size="sm" />
          Loading social providers...
        </p>
      ) : null}

      <div className="rounded-md border border-slate-700 bg-slate-900/40 p-3">
        <label className="text-xs text-slate-400">
          Ready Export Asset
          <select
            value={selectedExportId}
            onChange={(event) => setSelectedExportId(event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-[#7C3AED] focus:outline-none"
          >
            {readyExports.length ? null : <option value="">No ready exports available</option>}
            {readyExports.map((item) => (
              <option key={item.id} value={item.id}>
                {item.id.slice(0, 8)} • {item.aspect_ratio} • {item.caption_format}
              </option>
            ))}
          </select>
        </label>
        {!readyExports.length ? (
          <p className="mt-2 text-xs text-slate-500">
            Create and wait for a ready export before publishing.
          </p>
        ) : null}
      </div>

      <div className="rounded-md border border-slate-700 bg-slate-900/40 p-3">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-300">Universal Content</h4>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <label className="text-xs text-slate-400">
            Title
            <input
              value={universalFields.title}
              onChange={(event) => setUniversalFields((prev) => ({ ...prev, title: event.target.value }))}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-[#7C3AED] focus:outline-none"
            />
          </label>
          <label className="text-xs text-slate-400">
            Privacy
            <input
              value={universalFields.privacy}
              onChange={(event) => setUniversalFields((prev) => ({ ...prev, privacy: event.target.value }))}
              placeholder="private/public/unlisted"
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-[#7C3AED] focus:outline-none"
            />
          </label>
          <label className="text-xs text-slate-400 md:col-span-2">
            Caption
            <textarea
              value={universalFields.caption}
              onChange={(event) => setUniversalFields((prev) => ({ ...prev, caption: event.target.value }))}
              rows={2}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-[#7C3AED] focus:outline-none"
            />
          </label>
          <label className="text-xs text-slate-400 md:col-span-2">
            Description
            <textarea
              value={universalFields.description}
              onChange={(event) => setUniversalFields((prev) => ({ ...prev, description: event.target.value }))}
              rows={3}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-[#7C3AED] focus:outline-none"
            />
          </label>
          <label className="text-xs text-slate-400">
            Hashtags
            <input
              value={universalFields.hashtags}
              onChange={(event) => setUniversalFields((prev) => ({ ...prev, hashtags: event.target.value }))}
              placeholder="#clipbandit #podcast"
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-[#7C3AED] focus:outline-none"
            />
          </label>
          <label className="text-xs text-slate-400">
            Schedule Time (optional)
            <input
              type="datetime-local"
              value={universalFields.scheduled_for}
              onChange={(event) =>
                setUniversalFields((prev) => ({ ...prev, scheduled_for: event.target.value }))
              }
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-[#7C3AED] focus:outline-none"
            />
          </label>
        </div>
      </div>

      <div className="space-y-3">
        {PLATFORM_ORDER.map((platform) => {
          const provider = providersByPlatform[platform];
          const platformAccounts = accountsByPlatform[platform] || [];
          const draft = targetDrafts[platform];
          const latestJob = latestJobsByPlatform.get(platform);
          const providerName = provider?.display_name || platform;
          const providerReady = provider?.setup_status === "ready";
          const hasConnectedAccounts = platformAccounts.length > 0;

          return (
            <div key={platform} className="rounded-md border border-slate-700 bg-slate-900/30 p-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <label className="inline-flex items-center gap-2 text-sm text-slate-200">
                  <input
                    type="checkbox"
                    checked={draft?.enabled || false}
                    disabled={!providerReady || !hasConnectedAccounts}
                    onChange={(event) => handlePlatformToggle(platform, event.target.checked)}
                    className="h-4 w-4 rounded border-slate-600 bg-slate-950 text-[#7C3AED] focus:ring-[#7C3AED]"
                  />
                  <span className="font-medium">{providerName}</span>
                </label>
                {latestJob ? (
                  <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusStyles[latestJob.status]}`}>
                    {prettyStatus(latestJob.status)}
                  </span>
                ) : (
                  <span className="rounded-full bg-slate-800 px-2.5 py-1 text-xs text-slate-300">No jobs yet</span>
                )}
              </div>

              <p className="mt-2 text-xs text-slate-400">
                {!providerReady
                  ? provider?.setup_message || "Provider is not configured"
                  : hasConnectedAccounts
                    ? `${platformAccounts.length} account(s) connected`
                    : "No connected accounts. Connect one first."}
              </p>

              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <label className="text-xs text-slate-400">
                  Account
                  <select
                    value={draft?.connected_account_id || ""}
                    onChange={(event) => handlePlatformAccountChange(platform, event.target.value)}
                    disabled={!hasConnectedAccounts}
                    className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-[#7C3AED] focus:outline-none disabled:opacity-50"
                  >
                    {platformAccounts.length ? null : <option value="">No connected accounts</option>}
                    {platformAccounts.map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.display_name || account.username_or_channel_name || account.external_account_id}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="inline-flex items-center gap-2 text-xs text-slate-300">
                  <input
                    type="checkbox"
                    checked={draft?.use_override || false}
                    onChange={(event) => handleOverrideToggle(platform, event.target.checked)}
                    className="h-4 w-4 rounded border-slate-600 bg-slate-950 text-[#7C3AED] focus:ring-[#7C3AED]"
                  />
                  Use per-platform overrides
                </label>
              </div>

              {draft?.use_override ? (
                <div className="mt-3 grid gap-3 rounded-md border border-slate-700 bg-slate-950/50 p-3 md:grid-cols-2">
                  <label className="text-xs text-slate-400">
                    Title
                    <input
                      value={draft.override.title}
                      onChange={(event) => handleOverrideFieldChange(platform, "title", event.target.value)}
                      className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-[#7C3AED] focus:outline-none"
                    />
                  </label>
                  <label className="text-xs text-slate-400">
                    Privacy
                    <input
                      value={draft.override.privacy}
                      onChange={(event) => handleOverrideFieldChange(platform, "privacy", event.target.value)}
                      className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-[#7C3AED] focus:outline-none"
                    />
                  </label>
                  <label className="text-xs text-slate-400 md:col-span-2">
                    Caption
                    <textarea
                      value={draft.override.caption}
                      onChange={(event) => handleOverrideFieldChange(platform, "caption", event.target.value)}
                      rows={2}
                      className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-[#7C3AED] focus:outline-none"
                    />
                  </label>
                  <label className="text-xs text-slate-400 md:col-span-2">
                    Description
                    <textarea
                      value={draft.override.description}
                      onChange={(event) => handleOverrideFieldChange(platform, "description", event.target.value)}
                      rows={2}
                      className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-[#7C3AED] focus:outline-none"
                    />
                  </label>
                  <label className="text-xs text-slate-400">
                    Hashtags
                    <input
                      value={draft.override.hashtags}
                      onChange={(event) => handleOverrideFieldChange(platform, "hashtags", event.target.value)}
                      className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-[#7C3AED] focus:outline-none"
                    />
                  </label>
                  <label className="text-xs text-slate-400">
                    Schedule Time
                    <input
                      type="datetime-local"
                      value={draft.override.scheduled_for}
                      onChange={(event) => handleOverrideFieldChange(platform, "scheduled_for", event.target.value)}
                      className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-[#7C3AED] focus:outline-none"
                    />
                  </label>
                </div>
              ) : null}

              {latestJob?.error_message ? <p className="mt-3 text-xs text-red-400">{latestJob.error_message}</p> : null}
              {latestJob?.external_post_url ? (
                <a
                  href={latestJob.external_post_url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-3 inline-flex text-xs text-[#A78BFA] hover:text-[#C4B5FD]"
                >
                  Open published post
                </a>
              ) : null}
              {latestJob && (latestJob.status === "failed" || latestJob.status === "provider_not_configured") ? (
                <button
                  type="button"
                  onClick={() => void handleRetry(latestJob.id)}
                  disabled={retryingJobId === latestJob.id}
                  className="mt-3 inline-flex rounded-md border border-slate-700 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800 disabled:opacity-60"
                >
                  {retryingJobId === latestJob.id ? "Retrying..." : "Retry"}
                </button>
              ) : null}
            </div>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => void handleCreatePublishJobs()}
          disabled={publishing || !selectedExportId || !readyExports.length}
          className="rounded-md bg-[#7C3AED] px-4 py-2 text-sm font-medium text-white hover:bg-[#6D28D9] disabled:opacity-60"
        >
          {publishing ? "Publishing..." : "Publish Selected Platforms"}
        </button>
        <button
          type="button"
          onClick={() => void loadPublishJobs(selectedExportId)}
          disabled={loadingJobs || !selectedExportId}
          className="rounded-md border border-slate-700 px-3 py-2 text-sm text-slate-200 hover:bg-slate-800 disabled:opacity-60"
        >
          {loadingJobs ? "Refreshing..." : "Refresh Status"}
        </button>
      </div>

      {publishJobs.length ? (
        <div className="space-y-2 rounded-md border border-slate-700 bg-slate-900/40 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-300">Per-platform Publish Jobs</p>
          {publishJobs.map((job) => (
            <div key={job.id} className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-slate-700 bg-slate-950/60 px-3 py-2">
              <div className="text-xs text-slate-300">
                <span className="font-medium">{providersByPlatform[job.platform]?.display_name || job.platform}</span>{" "}
                • {job.id.slice(0, 8)}
                {job.external_post_id ? ` • ${job.external_post_id}` : ""}
              </div>
              <span className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${statusStyles[job.status]}`}>
                {prettyStatus(job.status)}
              </span>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
