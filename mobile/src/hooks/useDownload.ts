/**
 * MediaGrab Mobile - useDownload Hook (Fixed v1.0.0)
 * Handles the full download lifecycle:
 *   start → WS progress (polling fallback) → complete/error/cancel
 * 
 * Fixed in v1.0.0:
 * - Resolved stale closure bugs in WebSocket fallback
 * - Added download timeout (30 minutes)
 * - Proper state management with refs
 */

import { useCallback, useRef, useState, useEffect } from "react";
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

const DOWNLOAD_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes

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
  output_dir?: string;
  playlist_items?: number[];
  selected_urls?: string[];
  playlist_name?: string;
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

  // Use refs for mutable values to avoid stale closures
  const stateRef = useRef<DownloadState>("idle");
  const pollerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const cleanupWsRef = useRef<(() => void) | null>(null);
  const cancelledRef = useRef(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Keep stateRef in sync
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  const stopTask = useCallback(() => {
    if (pollerRef.current) {
      clearInterval(pollerRef.current);
      pollerRef.current = null;
    }
    if (cleanupWsRef.current) {
      cleanupWsRef.current();
      cleanupWsRef.current = null;
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  const handleUpdate = useCallback((data: ProgressInfo) => {
    // Use ref to check current state, not captured state
    if (cancelledRef.current) return;

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
    if (pollerRef.current) return; // Already polling

    pollerRef.current = setInterval(async () => {
      // Check ref instead of captured state
      if (cancelledRef.current || 
          stateRef.current === "complete" || 
          stateRef.current === "error" || 
          stateRef.current === "cancelled") {
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

  const start = useCallback(async (params: StartParams) => {
    // Reset all refs and state
    cancelledRef.current = false;
    stopTask();
    
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

      // Try WebSocket first - use function that checks ref, not captured state
      cleanupWsRef.current = createProgressSocket(
        id,
        (data: ProgressInfo) => {
          wsEstablished = true;
          handleUpdate(data);
        },
        () => {
          // Fixed: Check ref instead of captured state variable
          if (!cancelledRef.current && 
              stateRef.current === "downloading" && 
              wsEstablished) {
            startFallbackPoller(id);
          }
        }
      );

      // If WS doesn't get established within 3s, start polling
      // Fixed: Check ref instead of captured state
      timeoutRef.current = setTimeout(() => {
        if (!wsEstablished && 
            !cancelledRef.current && 
            stateRef.current === "downloading") {
          startFallbackPoller(id);
        }
      }, 3000);

      // Add download timeout
      timeoutRef.current = setTimeout(() => {
        if (stateRef.current === "downloading" && !cancelledRef.current) {
          setState("error");
          setProgress({
            ...DEFAULT_PROGRESS,
            status: "error",
            message: "Download timed out after 30 minutes",
          });
          stopTask();
        }
      }, DOWNLOAD_TIMEOUT_MS);

    } catch (err: any) {
      setState("error");
      setProgress({
        ...DEFAULT_PROGRESS,
        status: "error",
        message: err?.message ?? "Failed to start download",
      });
    }
  }, [startFallbackPoller, handleUpdate, stopTask]);

  const cancel = useCallback(async () => {
    cancelledRef.current = true;
    stopTask();
    if (taskId) {
      try { await cancelDownload(taskId); } catch { }
    }
    setState("cancelled");
    setProgress((p: ProgressInfo) => ({ 
      ...p, 
      status: "cancelled", 
      message: "Cancelled by user" 
    }));
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
