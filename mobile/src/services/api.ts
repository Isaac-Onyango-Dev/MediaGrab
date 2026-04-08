/**
 * MediaGrab Mobile – API Service
 * Typed TypeScript client for the FastAPI backend.
 * Configure backend URL in the Settings screen.
 */

import AsyncStorage from "@react-native-async-storage/async-storage";
import {
    discoverBackend,
    stopBrowsing,
    initialize_zeroconf,
    stopZeroconf,
    getSavedBackendUrl,
    clearSavedBackendUrl,
} from "./discovery";

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

export interface VideoInfo {
    type: "video";
    platform: string;
    title: string;
    uploader: string;
    duration: number | null;
    duration_str: string;
    thumbnail: string | null;
    view_count: number | null;
    description: string;
}

export interface PlaylistEntry {
    title: string;
    id: string;
    url: string;
    duration: number | null;
    duration_str: string;
}

export interface PlaylistInfo {
    type: "playlist";
    platform: string;
    title: string;
    count: number;
    entries: PlaylistEntry[];
}

export type AnalysisResult = VideoInfo | PlaylistInfo;

export interface FormatInfo {
    label: string;
    height: number;
    fps: number;
}

export interface ProgressInfo {
    status: "pending" | "downloading" | "processing" | "complete" | "error" | "cancelled";
    progress: number;
    message: string;
    filename: string;
    speed: string;
    eta: string;
    current_item?: number | null;
    total_items?: number | null;
    output_dir?: string | null;
    items_done?: number;
    items_total?: number;
}

// ─────────────────────────────────────────────
// Config
// ─────────────────────────────────────────────

const DEFAULT_BACKEND = ""; // Empty: forces discovery or manual entry
const STORAGE_KEY = "@mediagrab_backend_url";
const API_KEY_STORAGE = "@mediagrab_api_key";

let _cachedUrl: string | null = null;
let _cachedApiKey: string | null = null;

export async function getBackendUrl(): Promise<string> {
    if (_cachedUrl) return _cachedUrl;
    try {
        const stored = await AsyncStorage.getItem(STORAGE_KEY);
        _cachedUrl = stored ?? DEFAULT_BACKEND;
        return _cachedUrl;
    } catch {
        return DEFAULT_BACKEND;
    }
}

export async function setBackendUrl(url: string): Promise<void> {
    const clean = url.replace(/\/$/, "");
    _cachedUrl = clean;
    await AsyncStorage.setItem(STORAGE_KEY, clean);
}

export async function getApiKey(): Promise<string> {
    if (_cachedApiKey !== null) return _cachedApiKey;
    try {
        const stored = await AsyncStorage.getItem(API_KEY_STORAGE);
        _cachedApiKey = stored ?? "";
        return _cachedApiKey;
    } catch {
        return "";
    }
}

export async function setApiKey(key: string): Promise<void> {
    _cachedApiKey = key;
    await AsyncStorage.setItem(API_KEY_STORAGE, key);
}

// ─────────────────────────────────────────────
// Base fetch helper (with timeout)
// ─────────────────────────────────────────────

const REQUEST_TIMEOUT_MS = 15_000;

async function api<T>(
    path: string,
    options: RequestInit = {},
    timeoutMs = REQUEST_TIMEOUT_MS,
): Promise<T> {
    const base = await getBackendUrl();
    const apiKey = await getApiKey();
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
        const headers: Record<string, string> = {
            "Content-Type": "application/json",
        };
        if (apiKey) {
            headers["X-API-Key"] = apiKey;
        }

        const res = await fetch(`${base}${path}`, {
            headers,
            signal: controller.signal,
            ...options,
        });

        if (!res.ok) {
            const body = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(body.detail ?? `HTTP ${res.status}`);
        }

        return res.json() as Promise<T>;
    } catch (err: any) {
        if (err.name === "AbortError") {
            throw new Error("Request timed out — is the server running?");
        }
        throw err;
    } finally {
        clearTimeout(timer);
    }
}

// ─────────────────────────────────────────────
// API Methods
// ─────────────────────────────────────────────

export async function checkHealth(): Promise<boolean> {
    try {
        const r = await api<{ status: string }>("/health", {}, 5_000);
        return r.status === "ok";
    } catch {
        return false;
    }
}

export async function analyzeUrl(url: string): Promise<AnalysisResult> {
    return api<AnalysisResult>("/analyze", {
        method: "POST",
        body: JSON.stringify({ url }),
    }, 60_000);
}

export async function getFormats(url: string): Promise<FormatInfo[]> {
    const r = await api<{ formats: FormatInfo[] }>("/formats", {
        method: "POST",
        body: JSON.stringify({ url }),
    }, 30_000);
    return r.formats;
}

export async function startDownload(params: {
    url: string;
    fmt: string;
    quality: string;
    output_dir?: string;
    playlist_items?: number[];
}): Promise<string> {
    const body: any = {
        url: params.url,
        fmt: params.fmt,
        quality: params.quality,
        playlist_items: params.playlist_items || [],
    };
    if (params.output_dir) {
        body.output_dir = params.output_dir;
    }
    const r = await api<{ task_id: string }>("/download/start", {
        method: "POST",
        body: JSON.stringify(body),
    });
    return r.task_id;
}

export async function startPlaylistDownload(params: {
    selected_urls: string[];
    playlist_name: string;
    fmt: string;
    quality: string;
    output_dir?: string;
}): Promise<string> {
    const body: any = {
        selected_urls: params.selected_urls,
        playlist_name: params.playlist_name,
        fmt: params.fmt,
        quality: params.quality,
    };
    if (params.output_dir) {
        body.output_dir = params.output_dir;
    }
    const r = await api<{ task_id: string }>("/download/playlist", {
        method: "POST",
        body: JSON.stringify(body),
    });
    return r.task_id;
}

export async function getProgress(taskId: string): Promise<ProgressInfo> {
    return api<ProgressInfo>(`/download/progress/${taskId}`);
}

export async function cancelDownload(taskId: string): Promise<void> {
    await api(`/download/cancel/${taskId}`, { method: "POST" });
}

// ─────────────────────────────────────────────
// WebSocket progress streaming
// ─────────────────────────────────────────────

export function createProgressSocket(
    taskId: string,
    onUpdate: (data: ProgressInfo) => void,
    onDone: () => void,
): () => void {
    let ws: WebSocket | null = null;
    let closed = false;

    getBackendUrl().then((base) => {
        if (closed) return;

        const wsUrl = base.replace(/^https?/, (m) => (m === "https" ? "wss" : "ws")) + `/ws/${taskId}`;
        ws = new WebSocket(wsUrl);

        ws.onmessage = (evt) => {
            try {
                const data: ProgressInfo = JSON.parse(evt.data);
                onUpdate(data);
                if (["complete", "error", "cancelled"].includes(data.status)) {
                    ws?.close();
                    if (!closed) {
                        closed = true;
                        onDone();
                    }
                }
            } catch {
                // ignore parse errors
            }
        };

        ws.onerror = () => {
            if (!closed) {
                closed = true;
                onDone();
            }
        };

        ws.onclose = () => {
            if (!closed) {
                closed = true;
                onDone();
            }
        };
    }).catch(() => {
        if (!closed) {
            closed = true;
            onDone();
        }
    });

    return () => {
        closed = true;
        try { ws?.close(); } catch { /* ignore */ }
    };
}

// ─────────────────────────────────────────────
// mDNS Discovery re-exports
// ─────────────────────────────────────────────

export {
    discoverBackend,
    discoverBackendSubnetScan as discoverBackendIp,
    stopBrowsing,
    initialize_zeroconf,
    stopZeroconf,
    getSavedBackendUrl,
    clearSavedBackendUrl,
    autoConnect,
} from "./discovery";
