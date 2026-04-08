/**
 * MediaGrab Mobile – Connection Monitor Hook
 * Monitors backend server connectivity and provides auto-reconnect capability.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { checkHealth, getBackendUrl, discoverBackend, setBackendUrl } from "../services/api";

export type ConnectionStatus = "connected" | "disconnected" | "checking" | "reconnecting";

export function useConnectionMonitor() {
    const [status, setStatus] = useState<ConnectionStatus>("checking");
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const checkConnection = useCallback(async () => {
        const url = await getBackendUrl();
        if (!url) {
            setStatus("disconnected");
            return;
        }
        try {
            const ok = await checkHealth();
            setStatus(ok ? "connected" : "disconnected");
        } catch {
            setStatus("disconnected");
        }
    }, []);

    // Auto-reconnect attempt
    const attemptReconnect = useCallback(async () => {
        setStatus("reconnecting");
        try {
            const found = await discoverBackend();
            if (found) {
                await setBackendUrl(found);
                setStatus("connected");
                return true;
            }
        } catch { /* ignore */ }
        setStatus("disconnected");
        return false;
    }, []);

    // Start monitoring
    useEffect(() => {
        // Check immediately
        checkConnection();

        // Then check every 10 seconds
        intervalRef.current = setInterval(checkConnection, 10000);

        return () => {
            if (intervalRef.current) clearInterval(intervalRef.current);
        };
    }, [checkConnection]);

    return { status, checkConnection, attemptReconnect };
}
