/**
 * MediaGrab Mobile – Download Screen (v1.0.0 Production)
 * Format/quality selection → start download → real-time progress
 * 
 * v1.0.0 Fixes:
 * - Uses selectedFormat/selectedQuality from HomeScreen preferences
 * - Proper TypeScript navigation params
 * - Clean, focused UI
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
import { FormatInfo, getFormats, PlaylistEntry } from "../services/api";
import { ProgressBar, Chip, Card, Button } from "../components/ui";

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

interface DownloadScreenParams {
    url: string;
    title: string;
    platform: string;
    type?: "video" | "playlist";
    count?: number;
    entries?: PlaylistEntry[];
    selectedFormat?: "mp3" | "mp4";
    selectedQuality?: string;
    skipFormatSelection?: boolean;
}

interface Props {
    route: { params: DownloadScreenParams };
    navigation: {
        goBack: () => void;
        popToTop: () => void;
    };
}

export default function DownloadScreen({ route, navigation }: Props) {
    const { 
        url, 
        title, 
        platform, 
        type: contentType,
        count,
        entries,
        selectedFormat,
        selectedQuality,
        skipFormatSelection 
    } = route.params;
    const insets = useSafeAreaInsets();

    const { state: downloadState, progress, start, cancel, reset } = useDownload();

    const [fmt, setFmt] = useState<"mp3" | "mp4">(selectedFormat ?? "mp3");
    const [qualities, setQualities] = useState<FormatInfo[]>([]);
    const [quality, setQuality] = useState<string>(selectedQuality ?? "best");
    const [loadingQ, setLoadingQ] = useState(false);
    const [downloadingStarted, setDownloadingStarted] = useState(false);

    // Auto-start for single video when format selection skipped
    useEffect(() => {
        if (skipFormatSelection && !downloadingStarted && downloadState === "idle") {
            setDownloadingStarted(true);
            start({ url, fmt, quality: "best" });
        }
    }, [skipFormatSelection, downloadingStarted, downloadState, start, url, fmt]);

    // Fetch available qualities for MP4
    useEffect(() => {
        if (fmt === "mp4" && !skipFormatSelection) {
            setLoadingQ(true);
            getFormats(url)
                .then(qs => {
                    setQualities(qs);
                    if (qs.length > 0 && !selectedQuality) {
                        setQuality(qs[0].label);
                    }
                })
                .catch(() => setQualities([]))
                .finally(() => setLoadingQ(false));
        }
    }, [url, fmt, skipFormatSelection, selectedQuality]);

    const handleStartDownload = useCallback(() => {
        if (downloadState !== "idle") return;
        setDownloadingStarted(true);
        start({
            url,
            fmt,
            quality: fmt === "mp3" ? "best" : quality,
        });
    }, [downloadState, start, url, fmt, quality]);

    const handleCancel = useCallback(() => {
        cancel();
    }, [cancel]);

    const handleBack = useCallback(() => {
        if (downloadState === "idle" || downloadState === "complete" || downloadState === "error") {
            navigation.goBack();
        } else {
            Alert.alert(
                "Download in Progress",
                "Are you sure you want to cancel the current download?",
                [
                    { text: "Continue", style: "cancel" },
                    {
                        text: "Cancel Download",
                        style: "destructive",
                        onPress: () => {
                            cancel();
                            navigation.goBack();
                        }
                    }
                ]
            );
        }
    }, [downloadState, cancel, navigation]);

    // Download state display
    const stateDisplay = (): string => {
        switch (downloadState) {
            case "idle": return "Ready";
            case "starting": return "Starting…";
            case "downloading": return "Downloading";
            case "processing": return "Processing";
            case "complete": return "Complete";
            case "error": return "Failed";
            case "cancelled": return "Cancelled";
            default: return downloadState;
        }
    };

    const stateColor = (): string => {
        switch (downloadState) {
            case "downloading": return C.primary;
            case "processing": return C.warning;
            case "complete": return C.success;
            case "error":
            case "cancelled": return C.error;
            default: return C.textSub;
        }
    };

    return (
        <View style={[styles.root, { paddingTop: insets.top }]}>
            {/* Header */}
            <View style={styles.header}>
                <TouchableOpacity onPress={handleBack} style={styles.backBtn}>
                    <Text style={styles.backBtnText}>← Back</Text>
                </TouchableOpacity>
                <Text style={styles.headerTitle} numberOfLines={1}>{title}</Text>
            </View>

            <ScrollView 
                contentContainerStyle={styles.scroll}
                keyboardShouldPersistTaps="handled"
            >
                {/* Video Info Card */}
                <Card style={styles.infoCard}>
                    <Text style={styles.platformBadge}>
                        {platform === "youtube" ? "▶️" : platform === "tiktok" ? "🎵" : "🔗"} {platform}
                    </Text>
                    <Text style={styles.videoTitle} numberOfLines={2}>{title}</Text>
                    {contentType === "playlist" && count && (
                        <Text style={styles.subText}>📁 {count} videos in playlist</Text>
                    )}
                </Card>

                {/* Format Selection (only if not auto-starting) */}
                {!skipFormatSelection && downloadState === "idle" && (
                    <>
                        <Text style={styles.sectionLabel}>Format</Text>
                        <View style={styles.formatRow}>
                            <TouchableOpacity
                                style={[
                                    styles.formatBtn,
                                    fmt === "mp3" && styles.formatBtnActive
                                ]}
                                onPress={() => setFmt("mp3")}
                            >
                                <Text style={[
                                    styles.formatBtnText,
                                    fmt === "mp3" && styles.formatBtnTextActive
                                ]}>
                                    🎵 MP3
                                </Text>
                            </TouchableOpacity>
                            <TouchableOpacity
                                style={[
                                    styles.formatBtn,
                                    fmt === "mp4" && styles.formatBtnActive
                                ]}
                                onPress={() => setFmt("mp4")}
                            >
                                <Text style={[
                                    styles.formatBtnText,
                                    fmt === "mp4" && styles.formatBtnTextActive
                                ]}>
                                    🎬 MP4
                                </Text>
                            </TouchableOpacity>
                        </View>

                        {/* Quality Selection (MP4 only) */}
                        {fmt === "mp4" && (
                            <>
                                <Text style={styles.sectionLabel}>Quality</Text>
                                {loadingQ ? (
                                    <ActivityIndicator color={C.primary} />
                                ) : qualities.length > 0 ? (
                                    <View style={styles.qualityRow}>
                                        {qualities.map(q => (
                                            <Chip
                                                key={q.label}
                                                label={q.label}
                                                selected={quality === q.label}
                                                onPress={() => setQuality(q.label)}
                                            />
                                        ))}
                                    </View>
                                ) : (
                                    <Text style={styles.subText}>No quality options available</Text>
                                )}
                            </>
                        )}
                    </>
                )}

                {/* Download Progress */}
                {downloadState !== "idle" && (
                    <Card style={styles.progressCard}>
                        <View style={styles.progressHeader}>
                            <Text style={styles.statusLabel}>Status</Text>
                            <Text style={[styles.statusText, { color: stateColor() }]}>
                                {stateDisplay()}
                            </Text>
                        </View>

                        <ProgressBar 
                            progress={progress.progress}
                            status={downloadState}
                        />

                        {progress.speed && (
                            <Text style={styles.progressDetail}>⚡ {progress.speed}</Text>
                        )}
                        {progress.eta && (
                            <Text style={styles.progressDetail}>⏱ ETA: {progress.eta}</Text>
                        )}
                        {progress.filename && (
                            <Text style={styles.progressDetail} numberOfLines={1}>
                                📄 {progress.filename}
                            </Text>
                        )}

                        {(downloadState === "downloading" || downloadState === "processing") && (
                            <Button
                                label="Cancel"
                                onPress={handleCancel}
                                variant="danger"
                                style={styles.cancelBtn}
                            />
                        )}

                        {(downloadState === "complete" || downloadState === "error" || downloadState === "cancelled") && (
                            <Button
                                label="Done"
                                onPress={() => {
                                    reset();
                                    navigation.goBack();
                                }}
                                variant="primary"
                                style={styles.doneBtn}
                            />
                        )}
                    </Card>
                )}

                {/* Start Download Button */}
                {!skipFormatSelection && downloadState === "idle" && (
                    <Button
                        label={`Download ${fmt.toUpperCase()}`}
                        onPress={handleStartDownload}
                        variant="primary"
                        style={styles.downloadBtn}
                    />
                )}
            </ScrollView>
        </View>
    );
}

const styles = StyleSheet.create({
    root: {
        flex: 1,
        backgroundColor: C.bg,
    },
    header: {
        flexDirection: "row",
        alignItems: "center",
        paddingHorizontal: 16,
        paddingVertical: 12,
        borderBottomWidth: 1,
        borderBottomColor: C.border,
    },
    backBtn: {
        padding: 8,
    },
    backBtnText: {
        fontSize: 16,
        color: C.primary,
        fontWeight: "500",
    },
    headerTitle: {
        flex: 1,
        fontSize: 16,
        fontWeight: "600",
        color: C.text,
        marginLeft: 12,
    },
    scroll: {
        padding: 16,
        paddingBottom: 40,
    },
    infoCard: {
        marginBottom: 16,
    },
    platformBadge: {
        fontSize: 12,
        color: C.textSub,
        marginBottom: 8,
    },
    videoTitle: {
        fontSize: 16,
        fontWeight: "700",
        color: C.text,
        marginBottom: 6,
    },
    subText: {
        fontSize: 13,
        color: C.textSub,
        marginBottom: 2,
    },
    sectionLabel: {
        fontSize: 12,
        color: C.textSub,
        fontWeight: "600",
        marginBottom: 8,
        textTransform: "uppercase",
        letterSpacing: 0.5,
    },
    formatRow: {
        flexDirection: "row",
        gap: 8,
        marginBottom: 16,
    },
    formatBtn: {
        flex: 1,
        padding: 12,
        borderRadius: 8,
        alignItems: "center",
        borderWidth: 1,
        borderColor: C.border,
        backgroundColor: C.card,
    },
    formatBtnActive: {
        backgroundColor: C.primary,
        borderColor: C.primary,
    },
    formatBtnText: {
        color: C.textSub,
        fontWeight: "600",
    },
    formatBtnTextActive: {
        color: "#ffffff",
    },
    qualityRow: {
        flexDirection: "row",
        flexWrap: "wrap",
        gap: 8,
        marginBottom: 16,
    },
    progressCard: {
        marginBottom: 16,
    },
    progressHeader: {
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: 12,
    },
    statusLabel: {
        fontSize: 14,
        fontWeight: "600",
        color: C.text,
    },
    statusText: {
        fontSize: 14,
        fontWeight: "500",
    },
    progressDetail: {
        fontSize: 13,
        color: C.textSub,
        marginTop: 4,
    },
    cancelBtn: {
        marginTop: 16,
    },
    doneBtn: {
        marginTop: 16,
    },
    downloadBtn: {
        marginTop: 8,
    },
});
