import { AspectRatio, CaptionStyle } from "@/types";

export interface CaptionPreviewLayout {
  fontSizePx: number;
  lineHeight: number;
  marginXPercent: number;
  marginBottomPercent: number;
  maxCharsPerLine: number;
  maxLines: number;
}

interface CaptionStyleTheme {
  bold: boolean;
  italic: boolean;
  boxed: boolean;
  outlinePx: number;
  backgroundOpacity: number;
}

const STYLE_THEMES: Record<CaptionStyle, CaptionStyleTheme> = {
  bold_boxed: {
    bold: true,
    italic: false,
    boxed: true,
    outlinePx: 1,
    backgroundOpacity: 0.62,
  },
  sermon_quote: {
    bold: false,
    italic: true,
    boxed: false,
    outlinePx: 2,
    backgroundOpacity: 0.35,
  },
  clean_minimal: {
    bold: false,
    italic: false,
    boxed: false,
    outlinePx: 1.5,
    backgroundOpacity: 0.28,
  },
};

export function getCaptionPreviewLayout(
  captionStyle: CaptionStyle,
  aspectRatio: AspectRatio
): CaptionPreviewLayout {
  if (aspectRatio === "9:16") {
    return {
      fontSizePx:
        captionStyle === "bold_boxed"
          ? 26
          : captionStyle === "sermon_quote"
            ? 24
            : 23,
      lineHeight: 1.22,
      marginXPercent: 12,
      marginBottomPercent: 15,
      maxCharsPerLine: 20,
      maxLines: 3,
    };
  }

  return {
    fontSizePx:
      captionStyle === "bold_boxed"
        ? 34
        : captionStyle === "sermon_quote"
          ? 32
          : 31,
    lineHeight: 1.22,
    marginXPercent: 10,
    marginBottomPercent: 12,
    maxCharsPerLine: 28,
    maxLines: 3,
  };
}

export function getCaptionStyleTheme(captionStyle: CaptionStyle): CaptionStyleTheme {
  return STYLE_THEMES[captionStyle];
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
