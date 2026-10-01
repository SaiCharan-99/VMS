import type { ProcessType } from "@/types/api";

export const MAX_CONCURRENT_UPLOADS = 2;

export interface UploadSettings {
  process_type: ProcessType;
  awb?: string;
  order_ref?: string;
  station_id?: number;
}

/** Upload phase only; analysis progress comes from polling the job. */
export type UploadPhase = "queued" | "uploading" | "uploaded" | "error";

export interface UploadItem {
  id: string;
  file: File;
  settings: UploadSettings;
  phase: UploadPhase;
  progress: number;
  videoId?: number;
  jobId?: number;
  duplicate?: boolean;
  error?: string;
}

export type QueueAction =
  | { type: "add"; files: File[]; settings: UploadSettings; ids: string[] }
  | { type: "start"; id: string }
  | { type: "progress"; id: string; progress: number }
  | { type: "uploaded"; id: string; videoId: number; jobId?: number; duplicate: boolean }
  | { type: "error"; id: string; error: string }
  | { type: "remove"; id: string };

export function queueReducer(state: UploadItem[], action: QueueAction): UploadItem[] {
  const patch = (id: string, p: Partial<UploadItem>) =>
    state.map((it) => (it.id === id ? { ...it, ...p } : it));
  switch (action.type) {
    case "add":
      return [
        ...state,
        ...action.files.map((file, i) => ({
          id: action.ids[i] ?? `${file.name}-${state.length + i}`,
          file,
          settings: action.settings,
          phase: "queued" as const,
          progress: 0,
        })),
      ];
    case "start":
      return patch(action.id, { phase: "uploading", progress: 0 });
    case "progress":
      return patch(action.id, { progress: Math.max(0, Math.min(1, action.progress)) });
    case "uploaded":
      return patch(action.id, {
        phase: "uploaded",
        progress: 1,
        videoId: action.videoId,
        jobId: action.jobId,
        duplicate: action.duplicate,
      });
    case "error":
      return patch(action.id, { phase: "error", error: action.error });
    case "remove":
      return state.filter((it) => it.id !== action.id || it.phase === "uploading");
  }
}

/** Queued items that may start now without exceeding the concurrency limit. */
export function nextToStart(state: UploadItem[], max = MAX_CONCURRENT_UPLOADS): UploadItem[] {
  const running = state.filter((it) => it.phase === "uploading").length;
  return state.filter((it) => it.phase === "queued").slice(0, Math.max(0, max - running));
}

export const ACCEPTED_TYPES = ".mp4,.mov,.avi,.mkv,video/*";

export function isVideoFile(file: File): boolean {
  return file.type.startsWith("video/") || /\.(mp4|mov|avi|mkv)$/i.test(file.name);
}
