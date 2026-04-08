/**
 * MediaGrab Mobile – Download Screen
 * Format/quality selection → start download → real-time progress via WebSocket
 */

import React, { useCallback, useEffect, useState } from "react";
import {
    ActivityIndicator,
    Alert,
    Platform,
    ScrollView,
    StyleSheet,
    Text,
    TouchableOpacity,
    View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useDownload } from "../hooks/useDownload";
import { AnalysisResult, FormatInfo, getFormats, PlaylistEntry } from "../services/api";
import { ProgressBar, Chip, SectionLabel, Card, Button } from "../components/ui";

const C = {
    bg: "#0f0f0f",
    card: "#1a1a1a",
    border: "#2a2a2a",
    primary: "#3b82f6",
    success: "#22c55e",
    error: "#ef4444",
    warning: "#f59e0b",
    text: "#f1f5f9",
    textSub: "#94a3b8",
    pill: "#1e293b",
};

interface Props {
    route: { params: { url: string; result: AnalysisResult; selectedEntries?: PlaylistEntry[]; format?: "mp3" | "mp4"; skipFormatSelection?: boolean } };
    navigation: {
        navigate: (screen: string, params?: any) => void;
        goBack: () => void;
        popToTop: () => void;
    };
}

export default function DownloadScreen({ route, navigation }: Props) {
    const { url, result, selectedEntries: initialSelectedEntries, format: initialFormat, skipFormatSelection } = route.params;
    const insets = useSafeAreaInsets();

    const { state: downloadState, progress, start, cancel } = useDownload();

    const [fmt, setFmt] = useState<"mp3" | "mp4">(initialFormat ?? "mp3");
    const [qualities, setQualities] = useState<FormatInfo[]>([]);
    const [quality, setQuality] = useState<string>("best");
    const [loadingQ, setLoadingQ] = useState(false);
    const [downloadingStarted, setDownloadingStarted] = useState(false);

    const [selectedIds, setSelectedIds] = useState<Set<string>>(
        result.type === "playlist"
            ? new Set((initialSelectedEntries || result.entries).map((e: PlaylistEntry) => e.id))
            : new Set()
    );

    // Auto-start download when skipFormatSelection is true
    useEffect(() => {
        if (skipFormatSelection && !downloadingStarted && downloadState === "idle") {
            setDownloadingStarted(true);
            start({
                url,
                fmt,
                quality: fmt === "mp3" ? "best" : quality,
            });
        }
    }, [skipFormatSelection, downloadingStarted, downloadState, start, url, fmt, quality]);

    // FIX: Fetch qualities for playlists too (using first entry's URL)
    useEffect(() => {
        if (fmt === "mp4") {
            const qualityUrl = result.type === "playlist"
                ? result.entries[0]?.url
                : url;
            if (qualityUrl) {
                setLoadingQ(true);
                getFormats(qualityUrl)
                    .then((fmts: FormatInfo[]) => setQualities(fmts))
                    .catch(() => setQualities([]))
                    .finally(() => setLoadingQ(false));
            }
        }
    }, [fmt, result.type, url, result]);

    const handleDownload = useCallback(async () => {
        if (result.type === "playlist") {
            const selectedUrls = result.entries
                .filter(e => selectedIds.has(e.id))
                .map(e => e.url);

            if (selectedUrls.length === 0) {
                Alert.alert("No items selected", "Please select at least one item to download.");
                return;
            }

            await start({
                url,
                fmt,
                quality: fmt === "mp3" ? "best" : quality,
                selected_urls: selectedUrls,
                playlist_name: result.title,
            });
        } else {
            await start({
                url,
                fmt,
                quality: fmt === "mp3" ? "best" : quality,
            });
        }
    }, [url, fmt, quality, start, result, selectedIds]);

    const handleCancel = useCallback(async () => {
        await cancel();
    }, [cancel]);

    const toggleItem = (id: string) => {
        setSelectedIds(prev => {
            const next = new Set(prev);
            if (next.has(id)) {
                next.delete(id);
            } else {
                next.add(id);
            }
            return next;
        });
    };

    const selectAllItems = () => {
        if (result.type === "playlist") {
            setSelectedIds(new Set(result.entries.map((e) => e.id)));
        }
    };

    const deselectAllItems = () => {
        setSelectedIds(new Set());
    };

    const statusColor = () => {
        switch (progress.status) {
            case "complete": return C.success;
            case "error": return C.error;
            case "cancelled": return C.warning;
            default: return C.primary;
        }
    };

    const isOptionsPhase = downloadState === "idle";

    return (
        <ScrollView
            style={[styles.root, { paddingTop: insets.top }]}
            contentContainerStyle={styles.scroll}
            showsVerticalScrollIndicator={false}
        >
            <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
                <Text style={styles.backText}>← Back</Text>
            </TouchableOpacity>

            <Text style={styles.screenTitle}>Download</Text>

            <Card>
                <Text style={styles.videoTitle} numberOfLines={2}>
                    {result.type === "playlist" ? "🎵 " : "🎬 "}{result.title}
                </Text>
                {result.type === "video" && (
                    <Text style={styles.subText}>👤 {result.uploader}  ·  ⏱ {result.duration_str}</Text>
                )}
                {result.type === "playlist" && (
                    <Text style={styles.subText}>{result.count} videos</Text>
                )}
            </Card>

            {(isOptionsPhase && !skipFormatSelection) && (
                <>
                    <SectionLabel text="FORMAT" />
                    <View style={styles.chipRow}>
                        <Chip label="🎵 MP3 – Audio" selected={fmt === "mp3"} onPress={() => setFmt("mp3")} />
                        <Chip label="🎬 MP4 – Video" selected={fmt === "mp4"} onPress={() => setFmt("mp4")} />
                    </View>

                    {fmt === "mp4" && (
                        <>
                            <SectionLabel text="QUALITY" />
                            {loadingQ ? (
                                <ActivityIndicator color={C.primary} style={{ marginVertical: 12 }} />
                            ) : (
                                <View style={styles.chipRow}>
                                    <Chip
                                        label="⭐ Best"
                                        selected={quality === "best"}
                                        onPress={() => setQuality("best")}
                                    />
                                    {qualities.map((q: FormatInfo) => (
                                        <Chip
                                            key={q.label}
                                            label={`${q.label} @ ${q.fps}fps`}
                                            selected={quality === `bestvideo[height<=${q.height}]+bestaudio/best`}
                                            onPress={() => setQuality(`bestvideo[height<=${q.height}]+bestaudio/best`)}
                                        />
                                    ))}
                                </View>
                            )}
                        </>
                    )}

                    {result.type === "playlist" && (
                        <>
                            <SectionLabel text={`SELECT ITEMS (${selectedIds.size} / ${result.count})`} />
                            <View style={styles.chipRow}>
                                <Chip
                                    label="✓ Select All"
                                    selected={selectedIds.size === result.count}
                                    onPress={selectAllItems}
                                />
                                <Chip
                                    label="✗ Deselect All"
                                    selected={false}
                                    onPress={deselectAllItems}
                                />
                            </View>

                            <ScrollView style={styles.playlistBox} nestedScrollEnabled>
                                {result.entries.map((entry, idx) => (
                                    <TouchableOpacity
                                        key={entry.id || idx}
                                        style={[
                                            styles.playlistItem,
                                            selectedIds.has(entry.id) && styles.playlistItemSelected,
                                        ]}
                                        onPress={() => toggleItem(entry.id)}
                                    >
                                        <Text style={styles.playlistCheckbox}>
                                            {selectedIds.has(entry.id) ? "☑️" : "☐"}
                                        </Text>
                                        <View style={{ flex: 1 }}>
                                            <Text
                                                style={styles.playlistItemTitle}
                                                numberOfLines={1}
                                            >
                                                {idx + 1}. {entry.title}
                                            </Text>
                                            <Text style={styles.playlistItemDuration}>
                                                {entry.duration_str}
                                            </Text>
                                        </View>
                                    </TouchableOpacity>
                                ))}
                            </ScrollView>
                        </>
                    )}

                    <Button label="⬇️  Start Download" onPress={handleDownload} style={{ marginTop: 12 }} />
                </>
            )}

            {!isOptionsPhase && (
                <Card>
                    <Text style={[styles.statusLabel, { color: statusColor() }]}>
                        {downloadState === "complete" ? "✅ Download Complete!" :
                            downloadState === "error" ? "❌ Download Failed" :
                                downloadState === "cancelled" ? "⚠️ Download Cancelled" :
                                    "📥 Downloading…"}
                    </Text>

                    {progress.filename ? (
                        <Text style={styles.filename} numberOfLines={1}>{progress.filename}</Text>
                    ) : null}

                    {progress.current_item && progress.total_items ? (
                        <Text style={styles.itemProgress}>
                            Item {progress.current_item} of {progress.total_items}
                        </Text>
                    ) : null}

                    <ProgressBar progress={progress.progress} />

                    <View style={styles.statsRow}>
                        <Text style={styles.pctText}>{progress.progress.toFixed(1)}%</Text>
                        {progress.speed ? <Text style={styles.statText}>⚡ {progress.speed}</Text> : null}
                        {progress.eta ? <Text style={styles.statText}>⏱ ETA {progress.eta}</Text> : null}
                    </View>

                    {progress.message ? (
                        <Text style={styles.msgText}>{progress.message}</Text>
                    ) : null}

                    {downloadState === "complete" && progress.output_dir ? (
                        <Text style={styles.savedPathText}>
                            📁 Saved to: {progress.output_dir.replace(/^.*?MediaGrab/, "Downloads/MediaGrab")}
                        </Text>
                    ) : null}

                    {(downloadState === "downloading" || downloadState === "processing" || downloadState === "starting") && (
                        <Button
                            label="✖  Cancel"
                            variant="danger"
                            onPress={handleCancel}
                            style={{ marginTop: 14 }}
                        />
                    )}

                    {(downloadState === "complete" || downloadState === "error" || downloadState === "cancelled") && (
                        <Button
                            label="⬇️  Download Another"
                            onPress={() => navigation.popToTop()}
                            style={{ marginTop: 12 }}
                        />
                    )}
                </Card>
            )}
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    root: { flex: 1, backgroundColor: C.bg },
    scroll: { padding: 16, paddingBottom: 60 },
    backBtn: { marginBottom: 4 },
    backText: { color: C.primary, fontSize: 15, fontWeight: "600" },
    screenTitle: { fontSize: 26, fontWeight: "800", color: C.text, marginBottom: 16 },

    videoTitle: { fontSize: 15, fontWeight: "700", color: C.text, marginBottom: 4 },
    subText: { fontSize: 13, color: C.textSub },

    chipRow: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 16 },

    statusLabel: { fontSize: 16, fontWeight: "800", marginBottom: 10 },
    filename: { fontSize: 12, color: C.textSub, fontFamily: Platform.OS === "ios" ? "Menlo" : "monospace", marginBottom: 8 },
    itemProgress: { fontSize: 11, color: C.textSub, marginBottom: 8, fontWeight: "600" },
    savedPathText: { fontSize: 12, color: C.success, marginTop: 8, paddingHorizontal: 8, paddingVertical: 6, backgroundColor: C.pill, borderRadius: 6 },
    statsRow: { flexDirection: "row", alignItems: "center", gap: 12, marginTop: 8 },
    pctText: { fontSize: 14, fontWeight: "700", color: C.text },
    statText: { fontSize: 12, color: C.textSub },
    msgText: { fontSize: 12, color: C.textSub, marginTop: 6 },

    playlistBox: { maxHeight: 240, marginBottom: 12, borderRadius: 10, backgroundColor: C.card, borderWidth: 1, borderColor: C.border },
    playlistItem: { flexDirection: "row", alignItems: "center", padding: 12, borderBottomWidth: 1, borderBottomColor: C.border },
    playlistItemSelected: { backgroundColor: C.border },
    playlistCheckbox: { fontSize: 16, marginRight: 10, width: 24 },
    playlistItemTitle: { fontSize: 13, fontWeight: "600", color: C.text, marginBottom: 2 },
    playlistItemDuration: { fontSize: 11, color: C.textSub },
});
