/**
 * MediaGrab Discovery Service
 * Auto-discovers MediaGrab backend via mDNS/Zeroconf on local network
 * Falls back to manual entry if not found within timeout
 */

import ZeroConf from "react-native-zeroconf";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { getBackendUrl, setBackendUrl } from "./api";

const MEDIAGRAB_SERVICE = "_mediagrab._tcp.";
const DISCOVERY_TIMEOUT_MS = 8000;
const HEALTH_CHECK_TIMEOUT_MS = 2000;
const STORAGE_KEY = "@mediagrab_backend_url";

let zeroconf: ZeroConf | null = null;
let discoveryTimeoutHandle: ReturnType<typeof setTimeout> | null = null;

export function initialize_zeroconf(): void {
    if (zeroconf) return;
    zeroconf = new ZeroConf();
}

export function stopZeroconf(): void {
    if (zeroconf) {
        try {
            zeroconf.stop();
            zeroconf.removeDeviceListeners();
        } catch (e) {
            // Ignore cleanup errors
        }
        zeroconf = null;
    }
}

async function healthCheck(ip: string, port: number = 8000): Promise<boolean> {
    try {
        const url = `http://${ip}:${port}/health`;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), HEALTH_CHECK_TIMEOUT_MS);

        try {
            const response = await fetch(url, {
                method: "GET",
                signal: controller.signal,
            });
            clearTimeout(timeoutId);
            return response.ok && response.status === 200;
        } catch (e) {
            clearTimeout(timeoutId);
            return false;
        }
    } catch (e) {
        return false;
    }
}

function extractIp(addresses: string[]): string | null {
    if (!addresses || addresses.length === 0) return null;
    const validIps = addresses.filter((ip) =>
        /^\d+\.\d+\.\d+\.\d+$/.test(ip)
    );
    return validIps.length > 0 ? validIps[0] : null;
}

export async function discoverBackend(): Promise<string | null> {
    return new Promise((resolve) => {
        if (!zeroconf) initialize_zeroconf();

        let foundService = false;

        discoveryTimeoutHandle = setTimeout(() => {
            if (!foundService) {
                stopBrowsing();
                resolve(null);
            }
        }, DISCOVERY_TIMEOUT_MS);

        const handleServiceFound = async (service: any) => {
            if (foundService) return;

            try {
                const ip = extractIp(service.addresses || []);
                const port = service.port || 8000;

                if (!ip) {
                    console.warn("No valid IP found in Zeroconf service");
                    return;
                }

                const isHealthy = await healthCheck(ip, port);
                if (!isHealthy) {
                    console.warn(`Health check failed for ${ip}:${port}`);
                    return;
                }

                foundService = true;
                const url = `http://${ip}:${port}`;

                try {
                    await setBackendUrl(url);
                } catch (e) {
                    console.error("Failed to save discovered URL:", e);
                }

                if (discoveryTimeoutHandle) {
                    clearTimeout(discoveryTimeoutHandle);
                    discoveryTimeoutHandle = null;
                }

                stopBrowsing();
                resolve(url);
            } catch (e) {
                console.error("Error processing discovered service:", e);
            }
        };

        const handleServiceRemoved = () => {
            // Ignore removals during active discovery
        };

        // FIX: Remove existing listeners before attaching new ones to prevent leaks
        (zeroconf as any)?.removeAllListeners?.("resolved");
        (zeroconf as any)?.removeAllListeners?.("lost");

        zeroconf?.on("resolved", handleServiceFound);
        zeroconf?.on("lost", handleServiceRemoved);

        try {
            zeroconf?.scan(MEDIAGRAB_SERVICE, "tcp", "local.");
        } catch (e) {
            console.error("Failed to start Zeroconf scan:", e);
            stopBrowsing();
            resolve(null);
        }
    });
}

export function stopBrowsing(): void {
    try {
        if (zeroconf) {
            zeroconf.stop();
        }
    } catch (e) {
        // Ignore errors
    }

    if (discoveryTimeoutHandle) {
        clearTimeout(discoveryTimeoutHandle);
        discoveryTimeoutHandle = null;
    }
}

export async function getSavedBackendUrl(): Promise<string | null> {
    try {
        return await AsyncStorage.getItem(STORAGE_KEY);
    } catch (e) {
        return null;
    }
}

export async function clearSavedBackendUrl(): Promise<void> {
    try {
        await AsyncStorage.removeItem(STORAGE_KEY);
    } catch (e) {
        console.error("Failed to clear saved backend URL:", e);
    }
}

/**
 * autoConnect — chains all discovery methods: mDNS -> subnet scan -> last-known fallback.
 * Call this once at app start; it handles the entire connection flow.
 * @param onProgress optional callback for status messages shown to the user
 * @returns the connected backend URL, or null if every method failed
 */
export async function autoConnect(onProgress?: (msg: string) => void): Promise<string | null> {
    // 1. Try mDNS first (fast, ~8 seconds)
    onProgress?.("Searching for MediaGrab server on your network...");
    let url = await discoverBackend();
    if (url) return url;

    // 2. Try subnet scan (slower, ~30 seconds but thorough)
    onProgress?.("mDNS not found, scanning local network...");
    url = await discoverBackendSubnetScan((msg) => onProgress?.(msg));
    if (url) return url;

    // 3. Try last-known saved URL
    const saved = await getSavedBackendUrl();
    if (saved) {
        onProgress?.("Trying last-known server...");
        try {
            const controller = new AbortController();
            const tid = setTimeout(() => controller.abort(), 3000);
            const resp = await fetch(`${saved}/health`, { signal: controller.signal });
            clearTimeout(tid);
            if (resp.ok) return saved;
        } catch { /* server not reachable */ }
    }

    return null; // All methods failed
}

export async function discoverBackendSubnetScan(onProgress?: (msg: string) => void): Promise<string | null> {
    const controller = new AbortController();
    const globalTimeout = setTimeout(() => controller.abort(), 30000);

    try {
        const subnets = ["192.168.1", "192.168.0", "10.0.0", "172.16.0", "192.168.8"];

        for (const subnet of subnets) {
            if (controller.signal.aborted) return null;
            onProgress?.(`Scanning ${subnet}.x...`);

            for (let chunk = 0; chunk < 256; chunk += 32) {
                if (controller.signal.aborted) return null;

                const promises = [];
                for (let i = chunk; i < Math.min(chunk + 32, 256); i++) {
                    const url = `http://${subnet}.${i}:8000`;
                    const reqController = new AbortController();
                    const tid = setTimeout(() => reqController.abort(), 400);

                    promises.push(
                        fetch(`${url}/health`, {
                            method: 'GET',
                            headers: { 'Content-Type': 'application/json' },
                            signal: reqController.signal
                        })
                            .then(async (res) => {
                                clearTimeout(tid);
                                if (!res.ok) return null;
                                const data = await res.json();
                                return data.status === 'ok' ? url : null;
                            })
                            .catch(() => {
                                clearTimeout(tid);
                                return null;
                            })
                    );
                }

                const results = await Promise.all(promises);
                const found = results.find(r => r !== null);
                if (found) return found;
            }
        }
    } finally {
        clearTimeout(globalTimeout);
    }

    return null;
}
