/**
 * MediaGrab Mobile – useDownload hook
 * Handles the full download lifecycle:
 *   start → WS progress (polling fallback) → complete/error/cancel
 */

import { useCallback, useRef, useState } from "react";
import {
  cancelDownload,
  createProgressSocket,
  getProgress,
  ProgressInfo,
  startDownload,
  startPlaylistDownload,
} from "../services/api";

export type DownloadState =
  | "idle"
  | "starting"
  | "downloading"
  | "processing"
  | "complete"
  | "error"
  | "cancelled";

interface UseDownloadResult {
  state: DownloadState;
  progress: ProgressInfo;
  taskId: string | null;
  start: (params: StartParams) => Promise<void>;
  cancel: () => Promise<void>;
  reset: () => void;
}

interface StartParams {
  url: string;
  fmt: string;
  quality: string;
  output_dir?: string;  // Optional - backend has defaults
  playlist_items?: number[];  // Deprecated (indices)
  selected_urls?: string[];   // New (individual URLs)
  playlist_name?: string;     // New (for folder naming)
}

const DEFAULT_PROGRESS: ProgressInfo = {
  status: "pending",
  progress: 0,
  message: "",
  filename: "",
  speed: "",
  eta: "",
};

export function useDownload(): UseDownloadResult {
  const [state, setState] = useState<DownloadState>("idle");
  const [progress, setProgress] = useState<ProgressInfo>(DEFAULT_PROGRESS);
  const [taskId, setTaskId] = useState<string | null>(null);

  const pollerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const cleanupWsRef = useRef<(() => void) | null>(null);
  const cancelledRef = useRef(false);

  const stopTask = useCallback(() => {
    if (pollerRef.current) {
      clearInterval(pollerRef.current);
      pollerRef.current = null;
    }
    if (cleanupWsRef.current) {
      cleanupWsRef.current();
      cleanupWsRef.current = null;
    }
  }, []);

  const handleUpdate = useCallback((data: ProgressInfo) => {
    setProgress(data);
    if (data.status === "downloading") setState("downloading");
    else if (data.status === "processing") setState("processing");
    else if (data.status === "complete") {
      setState("complete");
      stopTask();
    } else if (data.status === "error") {
      setState("error");
      stopTask();
    } else if (data.status === "cancelled") {
      setState("cancelled");
      stopTask();
    }
  }, [stopTask]);

  const startFallbackPoller = useCallback((id: string) => {
    pollerRef.current = setInterval(async () => {
      if (cancelledRef.current) {
        stopTask();
        return;
      }
      try {
        const data = await getProgress(id);
        handleUpdate(data);
      } catch {
        // network hiccup — keep polling
      }
    }, 1000);
  }, [stopTask, handleUpdate]);

  // ── Public API ──────────────────────────────────────────────────────

  const start = useCallback(async (params: StartParams) => {
    cancelledRef.current = false;
    setState("starting");
    setProgress(DEFAULT_PROGRESS);

    try {
      let id: string;
      if (params.selected_urls && params.playlist_name) {
        id = await startPlaylistDownload({
          selected_urls: params.selected_urls,
          playlist_name: params.playlist_name,
          fmt: params.fmt,
          quality: params.quality,
          output_dir: params.output_dir,
        });
      } else {
        id = await startDownload(params);
      }
      setTaskId(id);
      setState("downloading");

      let wsEstablished = false;

      // Try WebSocket first
      cleanupWsRef.current = createProgressSocket(
        id,
        (data: ProgressInfo) => {
          wsEstablished = true;
          handleUpdate(data);
        },
        () => {
          // If WS closes completely but we aren't done yet, fallback to polling
          if (!cancelledRef.current && state === "downloading" && wsEstablished) {
            startFallbackPoller(id);
          }
        }
      );

      // If WS doesn't get established within 3s, start polling
      setTimeout(() => {
        if (!wsEstablished && !cancelledRef.current && state === "downloading") {
          startFallbackPoller(id);
        }
      }, 3000);

    } catch (err: any) {
      setState("error");
      setProgress({
        ...DEFAULT_PROGRESS,
        status: "error",
        message: err?.message ?? "Failed to start download",
      });
    }
  }, [startFallbackPoller, handleUpdate, state]);

  const cancel = useCallback(async () => {
    cancelledRef.current = true;
    stopTask();
    if (taskId) {
      try { await cancelDownload(taskId); } catch { }
    }
    setState("cancelled");
    setProgress((p: ProgressInfo) => ({ ...p, status: "cancelled", message: "Cancelled by user" }));
  }, [taskId, stopTask]);

  const reset = useCallback(() => {
    stopTask();
    cancelledRef.current = false;
    setState("idle");
    setProgress(DEFAULT_PROGRESS);
    setTaskId(null);
  }, [stopTask]);

  return { state, progress, taskId, start, cancel, reset };
}
