"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Card } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { api, ApiError } from "@/lib/api";
import { CarouselTemplate } from "@/types";

export function TemplateGallery() {
  const [templates, setTemplates] = useState<CarouselTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    const run = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.get<CarouselTemplate[]>("/api/carousels/templates");
        if (!mounted) return;
        setTemplates(data);
      } catch (err) {
        if (!mounted) return;
        const message =
          err instanceof ApiError
            ? err.status === 401 || err.status === 403
              ? "Session expired, please log in again."
              : err.message
            : "Failed to load carousel templates";
        setError(message);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    void run();
    return () => {
      mounted = false;
    };
  }, []);

  if (loading) {
    return (
      <div className="inline-flex items-center gap-2 text-sm text-[var(--app-muted)]">
        <LoadingSpinner size="sm" />
        Loading templates...
      </div>
    );
  }

  if (error) {
    return <p className="text-sm text-red-700">{error}</p>;
  }

  if (!templates.length) {
    return (
      <Card>
        <p className="text-sm text-[var(--app-muted)]">No carousel templates are available yet.</p>
      </Card>
    );
  }

  return (
    <div className="grid gap-5 md:grid-cols-2">
      {templates.map((template) => (
        <Card key={template.id}>
          <div className="space-y-4">
            <img
              src={template.preview_url}
              alt={`${template.name} preview`}
              className="h-64 w-full rounded-md border border-[var(--app-border)] object-cover"
            />
            <div>
              <h3 className="text-lg font-semibold text-[var(--app-text)]">{template.name}</h3>
              <p className="mt-1 text-sm text-[var(--app-muted)]">{template.description}</p>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase tracking-wide text-[var(--app-subtle)]">
                {template.default_slides} slides
              </span>
              <Link
                href={`/carousels/new?template=${encodeURIComponent(template.id)}`}
                className="rounded-md bg-[#1D3FD0] px-3 py-2 text-sm font-medium text-white hover:bg-[#1633B8]"
              >
                Use this template
              </Link>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}
