/**
 * MediaGrab Mobile – Home Screen
 * URL input → analyze → show info → navigate to download
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import {
    Alert,
    KeyboardAvoidingView,
    Linking,
    Platform,
    ScrollView,
    StyleSheet,
    Text,
    TextInput,
    TouchableOpacity,
    View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import * as Clipboard from "expo-clipboard";
import { analyzeUrl, AnalysisResult, autoConnect, getSavedBackendUrl, setBackendUrl, initialize_zeroconf } from "../services/api";
import { Colors, Button, Card, PlatformBadge, Banner } from "../components/ui";
import { checkForUpdate, UpdateInfo } from "../services/update";
import { useConnectionMonitor } from "../hooks/useConnectionMonitor";
import { toMediaGrabError, MediaGrabError } from "../types/errors";
import packageJson from "../../package.json";

interface PlaylistCheckboxProps {
    id: string;
    title: string;
    duration: string;
    index: number;
    selected: boolean;
    onToggle: () => void;
}

const PlaylistCheckbox = ({ id, title, duration, index, selected, onToggle }: PlaylistCheckboxProps) => {
    return (
        <TouchableOpacity
            style={[styles.checkboxRow, selected && styles.checkboxRowSelected]}
            onPress={onToggle}
        >
            <View style={[styles.checkbox, selected && styles.checkboxChecked]}>
                {selected && <Text style={styles.checkmark}>✓</Text>}
            </View>
            <View style={{ flex: 1 }}>
                <Text style={styles.checkboxIndex}>{String(index).padStart(3, " ")}</Text>
                <Text style={styles.checkboxTitle} numberOfLines={1}>[{duration}] {title}</Text>
            </View>
        </TouchableOpacity>
    );
};

// ─────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────

interface VideoCardProps {
    result: AnalysisResult;
    selectedIds?: Set<string>;
    onSelectionChange?: (ids: Set<string>) => void;
}

const VideoCard = ({ result, selectedIds = new Set(), onSelectionChange }: VideoCardProps) => {
    if (result.type === "video") {
        return (
            <Card style={{ marginBottom: 12 }}>
                <PlatformBadge platform={result.platform} />
                <Text style={styles.videoTitle} numberOfLines={2}>{result.title}</Text>
                <Text style={styles.subText}>👤 {result.uploader}</Text>
                <Text style={styles.subText}>⏱ {result.duration_str}</Text>
            </Card>
        );
    }

    const playlistEntries = result.entries || [];

    const handleSelectAll = () => {
        const newSet = new Set<string>();
        playlistEntries.forEach(e => newSet.add(e.id));
        onSelectionChange?.(newSet);
    };

    const handleDeselectAll = () => {
        onSelectionChange?.(new Set<string>());
    };

    const handleToggle = (id: string) => {
        const newSet = new Set(selectedIds);
        if (newSet.has(id)) {
            newSet.delete(id);
        } else {
            newSet.add(id);
        }
        onSelectionChange?.(newSet);
    };

    return (
        <Card style={{ marginBottom: 12 }}>
            <PlatformBadge platform={result.platform} />
            <Text style={styles.videoTitle} numberOfLines={2}>🎵 {result.title}</Text>
            <Text style={styles.subText}>{result.count} videos in playlist</Text>

            <View style={styles.selectionBtnRow}>
                <TouchableOpacity
                    style={[styles.selectionBtn, styles.selectAllBtn]}
                    onPress={handleSelectAll}
                >
                    <Text style={styles.selectionBtnText}>Select All</Text>
                </TouchableOpacity>
                <TouchableOpacity
                    style={[styles.selectionBtn, styles.deselectAllBtn]}
                    onPress={handleDeselectAll}
                >
                    <Text style={styles.selectionBtnText}>Deselect All</Text>
                </TouchableOpacity>
            </View>

            <Text style={styles.selectionCount}>
                Selected: {selectedIds.size} / {result.count}
            </Text>

            <View style={styles.playlistContainer}>
                {playlistEntries.map((e, i) => (
                    <PlaylistCheckbox
                        key={e.id || i}
                        id={e.id}
                        title={e.title}
                        duration={e.duration_str}
                        index={i + 1}
                        selected={selectedIds.has(e.id)}
                        onToggle={() => handleToggle(e.id)}
                    />
                ))}
            </View>
        </Card>
    );
};

// ─────────────────────────────────────────────
// Main Screen
// ─────────────────────────────────────────────

interface Props {
    navigation: any;
}

export default function HomeScreen({ navigation }: Props) {
    const insets = useSafeAreaInsets();
    const [url, setUrl] = useState("");
    const [analyzing, setAnalyzing] = useState(false);
    const [result, setResult] = useState<AnalysisResult | null>(null);
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
    const [connectionStatus, setConnectionStatus] = useState<"checking" | "connected" | "failed" | "manual">("checking");
    const [statusMessage, setStatusMessage] = useState("Connecting...");
    const [manualUrl, setManualUrl] = useState("");
    const [manualTesting, setManualTesting] = useState(false);
    const [updateInfo, setUpdateInfo] = useState<UpdateInfo | null>(null);
    const [selectedFormat, setSelectedFormat] = useState<"mp3" | "mp4">("mp3");
    const { status: connectionMonitorStatus, attemptReconnect } = useConnectionMonitor();
    const inputRef = useRef<TextInput>(null);
    const autoAnalyzeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

    useEffect(() => {
        initialize_zeroconf();

        const connect = async () => {
            const foundUrl = await autoConnect((msg) => setStatusMessage(msg));
            if (foundUrl) {
                await setBackendUrl(foundUrl);
                setConnectionStatus("connected");
                setStatusMessage("Connected to MediaGrab server");
            } else {
                setConnectionStatus("manual");
                setStatusMessage("Server not found — enter the address below");
                // Try to load last-known URL into manual input
                const saved = await getSavedBackendUrl();
                if (saved) setManualUrl(saved);
            }
        };

        const checkForUpdates = async () => {
            try {
                const info = await checkForUpdate(packageJson.version);
                if (info) {
                    setUpdateInfo(info);
                }
            } catch {
                // Silently fail update check
            }
        };

        connect();
        checkForUpdates();
    }, []);

    const handleManualConnect = async () => {
        let testUrl = manualUrl.trim().replace(/\/$/, "");
        if (!testUrl.startsWith("http")) testUrl = `http://${testUrl}`;
        setManualTesting(true);
        try {
            const resp = await fetch(`${testUrl}/health`);
            if (resp.ok) {
                await setBackendUrl(testUrl);
                setConnectionStatus("connected");
                setStatusMessage("Connected!");
            } else {
                setConnectionStatus("failed");
                setStatusMessage("Server responded but isn't a MediaGrab backend");
            }
        } catch {
            setConnectionStatus("failed");
            setStatusMessage("Could not reach server — check the address and ensure backend is running");
        }
        setManualTesting(false);
    };

    const pasteFromClipboard = useCallback(async () => {
        const text = await Clipboard.getStringAsync();
        if (text && text.trim().startsWith("http")) {
            setUrl(text.trim());
            // Auto-analyze immediately after paste
            setAnalyzing(true);
            setResult(null);
            setSelectedIds(new Set());
            try {
                const res = await analyzeUrl(text.trim());
                setResult(res);
                if (res.type === "playlist" && res.entries) {
                    const allIds = new Set<string>();
                    res.entries.forEach(e => allIds.add(e.id));
                    setSelectedIds(allIds);
                }
            } catch (err: unknown) {
                const error = toMediaGrabError(err, "Could not analyze this URL.");
                Alert.alert("Analysis Failed", error.message);
            } finally {
                setAnalyzing(false);
            }
        } else {
            setUrl(text);
        }
    }, []);

    const handleUrlChange = useCallback((text: string) => {
        setUrl(text);
        // Auto-analyze when URL looks valid after 1 second debounce
        if (text.trim().startsWith("http") && text.length > 10) {
            if (autoAnalyzeTimer.current) clearTimeout(autoAnalyzeTimer.current);
            autoAnalyzeTimer.current = setTimeout(async () => {
                setAnalyzing(true);
                setResult(null);
                setSelectedIds(new Set());
                try {
                    const res = await analyzeUrl(text.trim());
                    setResult(res);
                    if (res.type === "playlist" && res.entries) {
                        const allIds = new Set<string>();
                        res.entries.forEach(e => allIds.add(e.id));
                        setSelectedIds(allIds);
                    }
                } catch (err: unknown) {
                    const error = toMediaGrabError(err, "Could not analyze this URL.");
                    Alert.alert("Analysis Failed", error.message);
                } finally {
                    setAnalyzing(false);
                }
            }, 1000);
        }
    }, []);

    const handleAnalyze = useCallback(async () => {
        const trimmed = url.trim();
        if (!trimmed) {
            return;
        }
        if (!trimmed.startsWith("http")) {
            return;
        }
        setAnalyzing(true);
        setResult(null);
        setSelectedIds(new Set());
        try {
            const res = await analyzeUrl(trimmed);
            setResult(res);
            if (res.type === "playlist" && res.entries) {
                const allIds = new Set<string>();
                res.entries.forEach(e => allIds.add(e.id));
                setSelectedIds(allIds);
            }
        } catch (err: unknown) {
            const error = toMediaGrabError(err, "Could not analyze this URL.");
            Alert.alert("Analysis Failed", error.message);
        } finally {
            setAnalyzing(false);
        }
    }, [url]);

    const handleDownload = useCallback(() => {
        if (!result) return;

        // For single videos, skip format selection and go straight to download
        if (result.type === "video") {
            navigation.navigate("Download", {
                url: url.trim(),
                result,
                format: selectedFormat,
                skipFormatSelection: true,
            });
        } else {
            // For playlists, still go to DownloadScreen for item selection
            const selectedEntries = result.entries.filter(e => selectedIds.has(e.id));
            navigation.navigate("Download", {
                url: url.trim(),
                result,
                selectedEntries,
                format: selectedFormat,
            });
        }
    }, [result, url, selectedFormat, selectedIds, navigation]);

    const handleSettings = useCallback(() => {
        navigation.navigate("Settings");
    }, [navigation]);

    return (
        <KeyboardAvoidingView
            style={[styles.root, { paddingTop: insets.top }]}
            behavior={Platform.OS === "ios" ? "padding" : "height"}
        >
            <ScrollView
                contentContainerStyle={styles.scroll}
                keyboardShouldPersistTaps="handled"
                showsVerticalScrollIndicator={false}
            >
                <View style={styles.header}>
                    <View>
                        <Text style={styles.appName}>🎬 MediaGrab</Text>
                        <Text style={styles.appSub}>Universal Video Downloader</Text>
                    </View>
                    <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                        {/* Connection status pill */}
                        <TouchableOpacity
                            style={{
                                flexDirection: "row",
                                alignItems: "center",
                                paddingHorizontal: 10,
                                paddingVertical: 4,
                                borderRadius: 12,
                                backgroundColor: connectionMonitorStatus === "connected" ? "#0f2922" : connectionMonitorStatus === "reconnecting" ? "#1a1a2e" : "#2d1f0f",
                                borderWidth: 1,
                                borderColor: connectionMonitorStatus === "connected" ? "#22c55e" : connectionMonitorStatus === "reconnecting" ? "#3b82f6" : "#f59e0b",
                            }}
                            onPress={connectionMonitorStatus === "disconnected" ? attemptReconnect : undefined}
                        >
                            <Text style={{ fontSize: 8, marginRight: 4 }}>
                                {connectionMonitorStatus === "connected" ? "🟢" : connectionMonitorStatus === "reconnecting" ? "🔄" : "🔴"}
                            </Text>
                            <Text style={{
                                fontSize: 10,
                                color: connectionMonitorStatus === "connected" ? "#22c55e" : connectionMonitorStatus === "reconnecting" ? "#3b82f6" : "#f59e0b",
                            }}>
                                {connectionMonitorStatus === "connected" ? "Online" : connectionMonitorStatus === "reconnecting" ? "Reconnecting..." : "Offline"}
                            </Text>
                        </TouchableOpacity>

                        {/* Settings button */}
                        <TouchableOpacity onPress={handleSettings} style={styles.settingsBtn}>
                            <Text style={{ fontSize: 20 }}>⚙️</Text>
                        </TouchableOpacity>
                    </View>
                </View>

                {updateInfo && (
                    <Banner
                        message={`🔄 New version ${updateInfo.version} available!`}
                        kind="info"
                        onPress={() => Alert.alert(
                            "Update Available",
                            `Version ${updateInfo.version}\n\n${updateInfo.releaseNotes.slice(0, 300)}`,
                            [
                                { text: "Download", onPress: () => Linking.openURL(updateInfo.downloadUrl) },
                                { text: "Later", style: "cancel" },
                            ]
                        )}
                    />
                )}

                {connectionStatus === "checking" && (
                    <View style={[styles.serverInfo, { backgroundColor: "#1a1a2e" }]}>
                        <Text style={[styles.serverWarnText, { color: "#3b82f6" }]}>
                            🔍 {statusMessage}
                        </Text>
                    </View>
                )}

                {connectionStatus === "connected" && (
                    <View style={{ flexDirection: "row", alignItems: "center", marginBottom: 12, backgroundColor: "#0f2922", borderRadius: 8, padding: 8, borderWidth: 1, borderColor: "#22c55e33" }}>
                        <Text style={{ color: "#22c55e", fontSize: 12, flex: 1 }}>{statusMessage}</Text>
                        <TouchableOpacity onPress={() => setConnectionStatus("manual")}>
                            <Text style={{ color: "#64748b", fontSize: 12 }}>Change</Text>
                        </TouchableOpacity>
                    </View>
                )}

                {connectionStatus === "manual" && (
                    <Card style={{ marginBottom: 12, borderColor: "#f59e0b", borderWidth: 1 }}>
                        <Text style={{ fontSize: 14, fontWeight: "700", marginBottom: 8, color: Colors.text }}>
                            🔌 Connect to MediaGrab Server
                        </Text>
                        <Text style={{ fontSize: 12, color: "#94a3b8", marginBottom: 10 }}>
                            Enter your computer's IP address (e.g., 192.168.1.100:8000)
                        </Text>
                        <TextInput
                            value={manualUrl}
                            onChangeText={setManualUrl}
                            placeholder="192.168.1.100:8000"
                            placeholderTextColor="#64748b"
                            style={{ backgroundColor: "#111", borderRadius: 8, padding: 10, fontSize: 14, color: "#f1f5f9", marginBottom: 8, borderWidth: 1, borderColor: Colors.border }}
                            keyboardType="url"
                            autoCapitalize="none"
                        />
                        <Button
                            label={manualTesting ? "Testing..." : "Connect"}
                            onPress={handleManualConnect}
                            loading={manualTesting}
                            variant="primary"
                        />
                        <Text style={{ color: "#ef4444", fontSize: 12, marginTop: 6 }}>⚠️ {statusMessage}</Text>
                    </Card>
                )}

                {connectionMonitorStatus === "disconnected" && connectionStatus === "connected" && (
                    <View style={{ backgroundColor: "#2d1f0f", borderRadius: 8, padding: 10, marginBottom: 12, borderWidth: 1, borderColor: "#f59e0b" }}>
                        <Text style={{ color: "#f59e0b", fontSize: 12, marginBottom: 6 }}>⚠️ Server disconnected — tap to reconnect</Text>
                        <Button label="Reconnect" onPress={attemptReconnect} variant="secondary" />
                    </View>
                )}

                <Card style={{ marginBottom: 12 }}>
                    <Text style={styles.label}>Video URL</Text>
                    <TextInput
                        ref={inputRef}
                        style={styles.input}
                        value={url}
                        onChangeText={handleUrlChange}
                        placeholder="Paste YouTube, TikTok, Vimeo URL…"
                        placeholderTextColor={Colors.textSub}
                        autoCapitalize="none"
                        autoCorrect={false}
                        keyboardType="url"
                        returnKeyType="go"
                        onSubmitEditing={handleAnalyze}
                    />
                    <View style={styles.btnRow}>
                        <Button
                            variant="secondary"
                            label="📋 Paste"
                            onPress={pasteFromClipboard}
                            style={{ flex: 1 }}
                        />
                        <Button
                            variant="primary"
                            label={analyzing ? "" : "🔍 Analyze"}
                            loading={analyzing}
                            onPress={handleAnalyze}
                            style={{ flex: 2 }}
                        />
                    </View>
                </Card>

                {!result && !analyzing && (
                    <View style={styles.platformHint}>
                        {["YouTube", "TikTok", "Instagram", "Facebook", "Twitter", "Vimeo", "Reddit", "+more"].map((p) => (
                            <View key={p} style={styles.pill}>
                                <Text style={styles.pillText}>{p}</Text>
                            </View>
                        ))}
                    </View>
                )}

                {result && (
                    <VideoCard
                        result={result}
                        selectedIds={selectedIds}
                        onSelectionChange={setSelectedIds}
                    />
                )}

                {result && result.type === "video" && (
                    <Card style={{ marginBottom: 12 }}>
                        <Text style={{ fontSize: 12, color: "#94a3b8", marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 }}>Format</Text>
                        <View style={{ flexDirection: "row", gap: 8, marginBottom: 12 }}>
                            <TouchableOpacity
                                style={[{ flex: 1, padding: 12, borderRadius: 8, alignItems: "center", borderWidth: 1 },
                                    selectedFormat === "mp3" ? { backgroundColor: "#0066cc", borderColor: "#0052a3" } : { borderColor: "#2a2a2a" }]}
                                onPress={() => setSelectedFormat("mp3")}
                            >
                                <Text style={{ color: selectedFormat === "mp3" ? "#fff" : "#94a3b8", fontWeight: "600" }}>🎵 MP3 Audio</Text>
                            </TouchableOpacity>
                            <TouchableOpacity
                                style={[{ flex: 1, padding: 12, borderRadius: 8, alignItems: "center", borderWidth: 1 },
                                    selectedFormat === "mp4" ? { backgroundColor: "#0066cc", borderColor: "#0052a3" } : { borderColor: "#2a2a2a" }]}
                                onPress={() => setSelectedFormat("mp4")}
                            >
                                <Text style={{ color: selectedFormat === "mp4" ? "#fff" : "#94a3b8", fontWeight: "600" }}>🎬 MP4 Video</Text>
                            </TouchableOpacity>
                        </View>
                    </Card>
                )}

                {result && (
                    <Button
                        label={result.type === "playlist"
                            ? `⬇️  Download Selected (${selectedIds.size}/${result.count})`
                            : `⬇️  Download ${selectedFormat.toUpperCase()}`
                        }
                        onPress={handleDownload}
                        disabled={result.type === "playlist" && selectedIds.size === 0}
                        style={{ marginTop: 4, opacity: result.type === "playlist" && selectedIds.size === 0 ? 0.5 : 1 }}
                    />
                )}
            </ScrollView>
        </KeyboardAvoidingView>
    );
}

// ─────────────────────────────────────────────
// Styles
// ─────────────────────────────────────────────

const styles = StyleSheet.create({
    root: { flex: 1, backgroundColor: Colors.bg },
    scroll: { padding: 16, paddingBottom: 40 },
    header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 16 },
    appName: { fontSize: 22, fontWeight: "800", color: Colors.text },
    appSub: { fontSize: 12, color: Colors.textSub, marginTop: 2 },
    settingsBtn: { padding: 8 },

    serverInfo: {
        borderRadius: 10,
        padding: 12,
        marginBottom: 12,
        borderWidth: 1,
        borderColor: Colors.border,
    },
    serverWarnText: { color: Colors.warning, fontSize: 13, textAlign: "center" },

    label: { fontSize: 12, color: Colors.textSub, fontWeight: "600", marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 },

    input: {
        backgroundColor: "#111",
        borderRadius: 10,
        padding: 12,
        fontSize: 14,
        color: Colors.text,
        borderWidth: 1,
        borderColor: Colors.border,
        marginBottom: 12,
    },
    btnRow: { flexDirection: "row", gap: 10 },

    platformHint: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginBottom: 12 },
    pill: { backgroundColor: Colors.pill, borderRadius: 20, paddingHorizontal: 12, paddingVertical: 5 },
    pillText: { color: Colors.textSub, fontSize: 12 },

    videoTitle: { fontSize: 16, fontWeight: "700", color: Colors.text, marginBottom: 6 },
    subText: { fontSize: 13, color: Colors.textSub, marginBottom: 2 },
    divider: { height: 1, backgroundColor: Colors.border, marginVertical: 10 },
    entryRow: { fontSize: 12, color: Colors.textSub, fontFamily: Platform.OS === "ios" ? "Menlo" : "monospace", marginBottom: 2 },

    selectionBtnRow: {
        flexDirection: "row",
        gap: 8,
        marginVertical: 10,
    },
    selectionBtn: {
        flex: 1,
        paddingVertical: 8,
        paddingHorizontal: 12,
        borderRadius: 8,
        alignItems: "center",
        borderWidth: 1,
    },
    selectAllBtn: {
        backgroundColor: "#0066cc",
        borderColor: "#0052a3",
    },
    deselectAllBtn: {
        backgroundColor: "#333",
        borderColor: Colors.border,
    },
    selectionBtnText: {
        color: Colors.text,
        fontSize: 12,
        fontWeight: "600",
    },
    selectionCount: {
        fontSize: 12,
        color: Colors.textSub,
        marginBottom: 10,
    },
    playlistContainer: {
        marginTop: 8,
        maxHeight: 400,
    },
    checkboxRow: {
        flexDirection: "row",
        alignItems: "center",
        paddingVertical: 8,
        paddingHorizontal: 8,
        borderRadius: 6,
        marginBottom: 4,
        backgroundColor: "transparent",
    },
    checkboxRowSelected: {
        backgroundColor: "#1a3a52",
    },
    checkbox: {
        width: 24,
        height: 24,
        borderRadius: 4,
        borderWidth: 2,
        borderColor: Colors.textSub,
        marginRight: 10,
        justifyContent: "center",
        alignItems: "center",
        backgroundColor: "transparent",
    },
    checkboxChecked: {
        borderColor: "#0066cc",
        backgroundColor: "#0066cc",
    },
    checkmark: {
        color: Colors.text,
        fontSize: 14,
        fontWeight: "bold",
    },
    checkboxIndex: {
        fontSize: 11,
        color: Colors.textSub,
        fontFamily: Platform.OS === "ios" ? "Menlo" : "monospace",
        marginBottom: 2,
    },
    checkboxTitle: {
        fontSize: 12,
        color: Colors.text,
    },
});
