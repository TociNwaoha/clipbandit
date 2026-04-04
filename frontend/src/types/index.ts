export type UserTier = "starter" | "creator" | "agency";

export interface User {
  id: string;
  email: string;
  tier: UserTier;
  videos_used: number;
  created_at: string;
  updated_at: string;
}

export type VideoSourceType = "upload" | "youtube";
export type VideoStatus =
  | "queued"
  | "downloading"
  | "transcribing"
  | "scoring"
  | "ready"
  | "error";

export interface Video {
  id: string;
  user_id: string;
  title: string | null;
  source_type: VideoSourceType;
  source_url: string | null;
  storage_key: string | null;
  source_download_url?: string | null;
  duration_sec: number | null;
  resolution: string | null;
  file_size_bytes: number | null;
  status: VideoStatus;
  error_message: string | null;
  clip_count: number;
  created_at: string;
  updated_at: string;
  thumbnail_url?: string | null;
}

export interface VideoListItem {
  id: string;
  title: string | null;
  status: VideoStatus;
  duration_sec: number | null;
  clip_count: number;
  created_at: string;
  thumbnail_url: string | null;
}

export interface TranscriptSegmentPayload {
  id: number;
  start: number;
  end: number;
  text: string;
  words: Array<{
    word: string;
    start: number;
    end: number;
    confidence?: number;
    segment_index?: number;
  }>;
}

export interface VideoTranscript {
  video_id: string;
  word_count: number;
  duration: number;
  language: string | null;
  full_text: string;
  segments: TranscriptSegmentPayload[];
}

export type ClipStatus = "pending" | "ready" | "exported";

export interface Clip {
  id: string;
  video_id: string;
  start_time: number;
  end_time: number;
  duration_sec: number | null;
  score: number | null;
  hook_score: number | null;
  energy_score: number | null;
  title: string | null;
  hashtags: string[] | null;
  title_options: string[] | null;
  hashtag_options: string[][] | null;
  copy_generation_status: string | null;
  copy_generation_error: string | null;
  thumbnail_key: string | null;
  thumbnail_url: string | null;
  transcript_text: string | null;
  status: ClipStatus;
  created_at: string;
  updated_at: string;
}

export type AspectRatio = "original" | "9:16" | "16:9" | "1:1";
export type CaptionStyle = "bold_boxed" | "sermon_quote" | "clean_minimal";
export type CaptionFormat = "burned_in" | "srt";
export type ExportStatus = "queued" | "rendering" | "ready" | "error";

export interface Export {
  id: string;
  clip_id: string;
  retry_of_export_id: string | null;
  user_id: string;
  aspect_ratio: AspectRatio;
  caption_style: CaptionStyle | null;
  caption_format: CaptionFormat;
  caption_vertical_position?: number | null;
  storage_key: string | null;
  srt_key: string | null;
  download_url: string | null;
  srt_download_url?: string | null;
  url_expires_at: string | null;
  status: ExportStatus;
  error_message: string | null;
  render_time_sec: number | null;
  reused?: boolean;
  video_id?: string | null;
  video_title?: string | null;
  clip_title?: string | null;
  clip_transcript_text?: string | null;
  clip_thumbnail_url?: string | null;
  clip_title_options?: string[] | null;
  clip_hashtag_options?: string[][] | null;
  clip_copy_generation_status?: string | null;
  clip_copy_generation_error?: string | null;
  created_at: string;
  updated_at: string;
}

export type JobStatus = "queued" | "running" | "done" | "failed";

export interface Job {
  id: string;
  video_id: string;
  type: string;
  payload: Record<string, unknown>;
  status: JobStatus;
  celery_task_id: string | null;
  attempts: number;
  max_attempts: number;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TranscriptSegment {
  id: string;
  video_id: string;
  word: string | null;
  start_time: number;
  end_time: number;
  confidence: number | null;
  segment_index: number | null;
  created_at: string;
}
