import { AspectRatio, CaptionStyle } from "@/types";

export interface CaptionPreviewLayout {
  fontSizePx: number;
  lineHeight: number;
  marginXPercent: number;
  marginBottomPercent: number;
  maxCharsPerLine: number;
  maxLines: number;
}

export interface CaptionStyleTheme {
  bold: boolean;
  italic: boolean;
  boxed: boolean;
  outlinePx: number;
  backgroundOpacity: number;
  fontFamily: string;
}

export interface CaptionStyleMeta {
  value: CaptionStyle;
  label: string;
  description: string;
  theme: CaptionStyleTheme;
  fontSizeOffsetPx: number;
}

const CAPTION_STYLE_META: CaptionStyleMeta[] = [
  {
    value: "bold_boxed",
    label: "Bold Boxed",
    description: "High-contrast boxed text for quick readability.",
    theme: {
      bold: true,
      italic: false,
      boxed: true,
      outlinePx: 1,
      backgroundOpacity: 0.62,
      fontFamily: "Arial, Helvetica, sans-serif",
    },
    fontSizeOffsetPx: 3,
  },
  {
    value: "sermon_quote",
    label: "Sermon Quote",
    description: "Italic quote style for reflective speaking clips.",
    theme: {
      bold: false,
      italic: true,
      boxed: false,
      outlinePx: 2,
      backgroundOpacity: 0.35,
      fontFamily: "Arial, Helvetica, sans-serif",
    },
    fontSizeOffsetPx: 1,
  },
  {
    value: "clean_minimal",
    label: "Clean Minimal",
    description: "Simple low-noise subtitle style.",
    theme: {
      bold: false,
      italic: false,
      boxed: false,
      outlinePx: 1.5,
      backgroundOpacity: 0.28,
      fontFamily: "Arial, Helvetica, sans-serif",
    },
    fontSizeOffsetPx: 0,
  },
  {
    value: "kinetic_bold",
    label: "Kinetic Bold",
    description: "Punchy bold blocks with extra emphasis.",
    theme: {
      bold: true,
      italic: false,
      boxed: true,
      outlinePx: 0.8,
      backgroundOpacity: 0.72,
      fontFamily: "Arial, Helvetica, sans-serif",
    },
    fontSizeOffsetPx: 5,
  },
  {
    value: "cinema_outline",
    label: "Cinema Outline",
    description: "Cinematic outlined text with minimal backdrop.",
    theme: {
      bold: true,
      italic: false,
      boxed: false,
      outlinePx: 3,
      backgroundOpacity: 0.12,
      fontFamily: "Arial, Helvetica, sans-serif",
    },
    fontSizeOffsetPx: 2,
  },
  {
    value: "clean_highlight",
    label: "Clean Highlight",
    description: "Clean style with a subtle highlight bar.",
    theme: {
      bold: false,
      italic: false,
      boxed: true,
      outlinePx: 0.6,
      backgroundOpacity: 0.45,
      fontFamily: "Arial, Helvetica, sans-serif",
    },
    fontSizeOffsetPx: 1,
  },
];

const STYLE_META_BY_VALUE: Record<CaptionStyle, CaptionStyleMeta> = Object.fromEntries(
  CAPTION_STYLE_META.map((item) => [item.value, item])
) as Record<CaptionStyle, CaptionStyleMeta>;

export function getCaptionStyleOptions(): CaptionStyleMeta[] {
  return CAPTION_STYLE_META;
}

export function getCaptionStyleMeta(captionStyle: CaptionStyle): CaptionStyleMeta {
  return STYLE_META_BY_VALUE[captionStyle] || STYLE_META_BY_VALUE.clean_minimal;
}

export function formatCaptionStyleLabel(captionStyle: CaptionStyle | null | undefined): string {
  if (!captionStyle) return "No style";
  return getCaptionStyleMeta(captionStyle).label;
}

export function getCaptionPreviewLayout(
  captionStyle: CaptionStyle,
  aspectRatio: AspectRatio,
  sourceAspectRatio?: number | null
): CaptionPreviewLayout {
  const effectiveAspect =
    aspectRatio === "original"
      ? sourceAspectRatio && sourceAspectRatio < 0.92
        ? "9:16"
        : sourceAspectRatio && sourceAspectRatio > 1.08
          ? "16:9"
          : "1:1"
      : aspectRatio;

  const styleMeta = getCaptionStyleMeta(captionStyle);

  if (effectiveAspect === "9:16") {
    return {
      fontSizePx: 23 + styleMeta.fontSizeOffsetPx,
      lineHeight: 1.22,
      marginXPercent: 12,
      marginBottomPercent: 15,
      maxCharsPerLine: 20,
      maxLines: 3,
    };
  }

  if (effectiveAspect === "16:9") {
    return {
      fontSizePx: 29 + styleMeta.fontSizeOffsetPx,
      lineHeight: 1.2,
      marginXPercent: 8,
      marginBottomPercent: 11,
      maxCharsPerLine: 34,
      maxLines: 3,
    };
  }

  return {
    fontSizePx: 31 + styleMeta.fontSizeOffsetPx,
    lineHeight: 1.22,
    marginXPercent: 10,
    marginBottomPercent: 12,
    maxCharsPerLine: 28,
    maxLines: 3,
  };
}

export function getCaptionStyleTheme(captionStyle: CaptionStyle): CaptionStyleTheme {
  return getCaptionStyleMeta(captionStyle).theme;
}

export function wrapCaptionPreviewText(
  text: string,
  maxCharsPerLine: number,
  maxLines: number
): string[] {
  const words = text
    .trim()
    .split(/\s+/)
    .filter(Boolean);

  if (!words.length) return [];

  const lines: string[] = [];
  let current = "";
  let idx = 0;

  while (idx < words.length && lines.length < maxLines) {
    const word = words[idx];
    const next = current ? `${current} ${word}` : word;
    if (current && next.length > maxCharsPerLine) {
      lines.push(current);
      current = "";
      continue;
    }
    current = next;
    idx += 1;
  }

  if (current && lines.length < maxLines) {
    lines.push(current);
  }

  if (idx < words.length && lines.length) {
    lines[lines.length - 1] = `${lines[lines.length - 1].replace(/[.,!?;:]+$/, "")}...`;
  }

  return lines.slice(0, maxLines);
}

export function buildCaptionPreviewText(transcriptText: string | null): string {
  const source = (transcriptText || "").replace(/\s+/g, " ").trim();
  if (!source) {
    return "Your caption preview appears here after transcript text is available.";
  }

  const words = source.split(" ");
  return words.slice(0, 22).join(" ");
}
