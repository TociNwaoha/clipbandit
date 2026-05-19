"use client";

import { CarouselRenderResponse } from "@/types";

interface SlidePreviewProps {
  result: CarouselRenderResponse | null;
}

export function SlidePreview({ result }: SlidePreviewProps) {
  if (!result) {
    return (
      <div className="rounded-lg border border-[var(--app-border)] bg-[var(--app-surface-soft)] p-4 text-sm text-[var(--app-muted)]">
        Render preview to see generated slides.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {result.slides.map((slide) => (
        <div key={slide.key} className="overflow-hidden rounded-md border border-[var(--app-border)]">
          <img src={slide.url} alt={`Slide ${slide.index}`} className="w-full object-cover" />
        </div>
      ))}
    </div>
  );
}
