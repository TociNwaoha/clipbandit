"use client";

import { useMemo, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/Button";

type UploadTab = "upload" | "youtube";

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploaded: () => Promise<void> | void;
}

interface UploadUrlResponse {
  video_id: string;
  upload_url: string;
  upload_fields: Record<string, string>;
  storage_key: string;
  use_local: boolean;
}

const MAX_UPLOAD_BYTES = 5_368_709_120;
const ACCEPTED_TYPES = new Set([
  "video/mp4",
  "video/quicktime",
  "video/x-msvideo",
  "video/x-matroska",
]);
const ACCEPTED_EXTENSIONS = new Set([".mp4", ".mov", ".avi", ".mkv"]);

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let value = bytes;
  let unitIndex = -1;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[unitIndex]}`;
}

function isYoutubeUrl(value: string): boolean {
  try {
    const parsed = new URL(value);
    if (!["http:", "https:"].includes(parsed.protocol)) return false;
    const host = parsed.hostname.toLowerCase().replace(/^www\./, "");
    return host === "youtube.com" || host === "youtu.be" || host.endsWith(".youtube.com");
  } catch {
    return false;
  }
}

function uploadWithXhr(upload: UploadUrlResponse, file: File, onProgress: (percent: number) => void) {
  return new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", upload.upload_url);

    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable) return;
      const percent = Math.min(100, Math.round((event.loaded / event.total) * 100));
      onProgress(percent);
    };

    xhr.onerror = () => reject(new Error("Upload failed. Please try again."));
    xhr.onabort = () => reject(new Error("Upload canceled"));
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        onProgress(100);
        resolve();
      } else {
        reject(new Error(`Upload failed with status ${xhr.status}`));
      }
    };

    const formData = new FormData();
    if (upload.use_local) {
      formData.append("key", upload.storage_key);
      formData.append("file", file);
    } else {
      Object.entries(upload.upload_fields || {}).forEach(([field, value]) => {
        formData.append(field, value);
      });
      if (!upload.upload_fields?.key) {
        formData.append("key", upload.storage_key);
      }
      formData.append("file", file);
    }

    xhr.send(formData);
  });
}

export function UploadModal({ isOpen, onClose, onUploaded }: UploadModalProps) {
  const [activeTab, setActiveTab] = useState<UploadTab>("upload");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const busy = uploading || importing;

  const youtubeValid = useMemo(() => youtubeUrl.trim() === "" || isYoutubeUrl(youtubeUrl.trim()), [youtubeUrl]);

  if (!isOpen) return null;

  const resetState = () => {
    setSelectedFile(null);
    setUploadProgress(0);
    setUploading(false);
    setImporting(false);
    setYoutubeUrl("");
    setError(null);
    setSuccessMessage(null);
    setIsDragging(false);
    setActiveTab("upload");
  };

  const closeModal = () => {
    if (busy) return;
    resetState();
    onClose();
  };

  const validateFile = (file: File): string | null => {
    if (file.size > MAX_UPLOAD_BYTES) return "File exceeds 5GB limit";
    if (file.type && !ACCEPTED_TYPES.has(file.type)) return "Unsupported file type";
    if (!file.type) {
      const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
      if (!ACCEPTED_EXTENSIONS.has(ext)) return "Unsupported file type";
    }
    return null;
  };

  const handleFileSelection = (file: File | null) => {
    if (!file) return;
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      setSelectedFile(null);
      return;
    }
    setError(null);
    setSuccessMessage(null);
    setSelectedFile(file);
  };

  const startUpload = async () => {
    if (!selectedFile || uploading) return;
    setError(null);
    setSuccessMessage(null);
    setUploading(true);
    setUploadProgress(0);

    try {
      const upload = await api.post<UploadUrlResponse>("/api/videos/upload-url", {
        filename: selectedFile.name,
        file_size: selectedFile.size,
        content_type: selectedFile.type || "video/mp4",
      });

      await uploadWithXhr(upload, selectedFile, setUploadProgress);
      await api.post("/api/videos/confirm-upload", { video_id: upload.video_id });

      setSuccessMessage("Video uploaded! Processing...");
      await onUploaded();
      window.setTimeout(() => {
        closeModal();
      }, 2000);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Upload failed";
      setError(message);
    } finally {
      setUploading(false);
    }
  };

  const importYoutube = async () => {
    if (importing) return;
    const normalized = youtubeUrl.trim();
    if (!isYoutubeUrl(normalized)) {
      setError("Please enter a valid YouTube URL (youtube.com or youtu.be)");
      return;
    }

    setImporting(true);
    setError(null);
    setSuccessMessage(null);
    try {
      await api.post("/api/videos/import-youtube", { url: normalized });
      setSuccessMessage("Import started! We'll process your video shortly.");
      await onUploaded();
      window.setTimeout(() => {
        closeModal();
      }, 2000);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Failed to start YouTube import";
      setError(message);
    } finally {
      setImporting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4"
      onClick={closeModal}
    >
      <div
        className="w-full max-w-2xl rounded-2xl border border-slate-700 bg-[#0F172A] shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <h2 className="text-lg font-semibold text-white">Add Video</h2>
          <button
            className="rounded-md p-2 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
            onClick={closeModal}
            disabled={busy}
            aria-label="Close"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        <div className="px-6 pt-4">
          <div className="inline-flex rounded-lg bg-slate-900 p-1">
            <button
              className={`rounded-md px-4 py-2 text-sm transition-colors ${
                activeTab === "upload" ? "bg-[#7C3AED] text-white" : "text-slate-300 hover:text-white"
              }`}
              onClick={() => {
                setActiveTab("upload");
                setError(null);
                setSuccessMessage(null);
              }}
            >
              Upload File
            </button>
            <button
              className={`rounded-md px-4 py-2 text-sm transition-colors ${
                activeTab === "youtube" ? "bg-[#7C3AED] text-white" : "text-slate-300 hover:text-white"
              }`}
              onClick={() => {
                setActiveTab("youtube");
                setError(null);
                setSuccessMessage(null);
              }}
            >
              YouTube URL
            </button>
          </div>
        </div>

        <div className="p-6">
          {activeTab === "upload" ? (
            <div>
              <input
                ref={fileInputRef}
                type="file"
                accept="video/mp4,video/quicktime,video/x-msvideo,video/x-matroska"
                className="hidden"
                onChange={(event) => handleFileSelection(event.target.files?.[0] || null)}
              />
              <button
                type="button"
                className={`w-full rounded-xl border-2 border-dashed px-6 py-14 text-center transition-colors ${
                  isDragging
                    ? "border-[#7C3AED] bg-[#7C3AED]/10"
                    : "border-slate-700 bg-[#1E293B]/40 hover:border-[#7C3AED]/80 hover:bg-[#7C3AED]/5"
                }`}
                onClick={() => fileInputRef.current?.click()}
                onDragOver={(event) => {
                  event.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={(event) => {
                  event.preventDefault();
                  setIsDragging(false);
                }}
                onDrop={(event) => {
                  event.preventDefault();
                  setIsDragging(false);
                  handleFileSelection(event.dataTransfer.files?.[0] || null);
                }}
              >
                <div className="mx-auto mb-3 w-fit rounded-full bg-[#7C3AED]/15 p-3 text-[#A78BFA]">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M12 16V4M12 4L7 9M12 4L17 9M4 16V18C4 19.1 4.9 20 6 20H18C19.1 20 20 19.1 20 18V16"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
                <p className="text-base font-medium text-white">Drag your video here or click to browse</p>
                <p className="mt-2 text-sm text-slate-400">Supports MP4, MOV, MKV, AVI · Max 5GB</p>
              </button>

              {selectedFile && (
                <div className="mt-4 rounded-xl border border-slate-700 bg-[#1E293B]/70 px-4 py-3">
                  <p className="truncate text-sm font-medium text-slate-100">{selectedFile.name}</p>
                  <p className="mt-1 text-xs text-slate-400">{formatBytes(selectedFile.size)}</p>
                </div>
              )}

              {uploading && (
                <div className="mt-4">
                  <div className="mb-1 flex items-center justify-between text-xs text-slate-400">
                    <span>Uploading...</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-800">
                    <div
                      className="h-full rounded-full bg-[#7C3AED] transition-all"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              )}

              <div className="mt-5 flex justify-end">
                <Button onClick={startUpload} loading={uploading} disabled={!selectedFile} className="min-w-40">
                  Start Processing
                </Button>
              </div>
            </div>
          ) : (
            <div>
              <label className="mb-2 block text-sm text-slate-300">YouTube URL</label>
              <input
                type="text"
                value={youtubeUrl}
                onChange={(event) => setYoutubeUrl(event.target.value)}
                placeholder="Paste YouTube URL..."
                disabled={importing}
                className="w-full rounded-lg border border-slate-700 bg-[#1E293B]/70 px-4 py-3 text-sm text-white
                           placeholder:text-slate-500 focus:border-[#7C3AED] focus:outline-none"
              />
              {!youtubeValid && <p className="mt-2 text-xs text-red-400">Only youtube.com or youtu.be links are allowed</p>}
              <div className="mt-5 flex justify-end">
                <Button onClick={importYoutube} disabled={!youtubeUrl.trim()} loading={importing} className="min-w-28">
                  Import
                </Button>
              </div>
            </div>
          )}

          {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
          {successMessage && <p className="mt-4 text-sm text-emerald-400">{successMessage}</p>}
        </div>
      </div>
    </div>
  );
}
