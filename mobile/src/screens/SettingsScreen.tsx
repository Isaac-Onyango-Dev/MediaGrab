/**
 * MediaGrab Mobile – Settings Screen
 */

import React, { useCallback, useEffect, useState } from "react";
import {
    Alert,
    ScrollView,
    StyleSheet,
    Text,
    TextInput,
    View,
    ViewStyle,
    Linking,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { checkHealth, discoverBackend, getBackendUrl, setBackendUrl, initialize_zeroconf, getApiKey, setApiKey } from "../services/api";
import { Colors, Button, Card } from "../components/ui";
import { checkForUpdate } from "../services/update";
import packageJson from "../../package.json";

export default function SettingsScreen({ navigation }: { 
    navigation: {
        navigate: (screen: string) => void;
        goBack: () => void;
    };
}) {
    const insets = useSafeAreaInsets();
    const [serverUrl, setServerUrl] = useState("");
    const [apiKey, setApiKeyLocal] = useState("");
    const [testing, setTesting] = useState(false);
    const [status, setStatus] = useState<"idle" | "ok" | "fail">("idle");

    const [format, setFormat] = useState("mp3");
    const [quality, setQuality] = useState("192k");

    const [scanning, setScanning] = useState(false);
    const [scanMsg, setScanMsg] = useState("");

    useEffect(() => {
        getBackendUrl().then(setServerUrl);
        getApiKey().then(setApiKeyLocal);
        AsyncStorage.getItem("@mediagrab_format").then(f => { if (f) setFormat(f); });
        AsyncStorage.getItem("@mediagrab_quality").then(q => { if (q) setQuality(q); });
        initialize_zeroconf();
    }, []);

    const handleSave = useCallback(async () => {
        const url = serverUrl.trim().replace(/\/$/, "");
        if (!url.startsWith("http")) {
            Alert.alert("Invalid URL", "Server URL must start with http:// or https://");
            return;
        }
        await setBackendUrl(url);
        await setApiKey(apiKey.trim());
        await AsyncStorage.setItem("@mediagrab_format", format);
        await AsyncStorage.setItem("@mediagrab_quality", quality);
        Alert.alert("Saved", "Settings updated.");
    }, [serverUrl, apiKey, format, quality]);

    const handleTest = useCallback(async () => {
        setTesting(true);
        setStatus("idle");
        const ok = await checkHealth();
        setStatus(ok ? "ok" : "fail");
        setTesting(false);
    }, []);

    const handleScan = useCallback(async () => {
        setScanning(true);
        setScanMsg("🔍 Scanning for MediaGrab server on local network (mDNS)...");
        try {
            const found = await discoverBackend();
            if (found) {
                setServerUrl(found);
                setStatus("ok");
                setScanMsg("");
                Alert.alert("✅ Server Found!", `Discovered at ${found}`);
            } else {
                setScanMsg("⚠️ Fallback: No mDNS service found. Enter server URL manually or try IP scanning.");
                Alert.alert("Not Found", "Could not find MediaGrab server via mDNS. Ensure backend is running on your local network.");
            }
        } catch (err) {
            setScanMsg("❌ Scan failed. Check network connection.");
            Alert.alert("Scan Error", "An error occurred during discovery. Try entering the IP manually.");
        } finally {
            setScanning(false);
            setTimeout(() => setScanMsg(""), 2000);
        }
    }, []);

    const handleCheckUpdate = useCallback(async () => {
        Alert.alert("Checking for updates...", undefined, [{ text: "OK" }]);
        const info = await checkForUpdate(packageJson.version);
        if (info) {
            Alert.alert(
                `Update Available: v${info.version}`,
                info.releaseNotes.slice(0, 500),
                [
                    { text: "Download", onPress: () => Linking.openURL(info.downloadUrl) },
                    { text: "Later", style: "cancel" },
                ]
            );
        } else {
            Alert.alert("Up to Date", `You are running the latest version (v${packageJson.version}).`);
        }
    }, []);

    return (
        <ScrollView
            style={[styles.root, { paddingTop: insets.top }]}
            contentContainerStyle={styles.scroll}
        >
            <View style={styles.header}>
                <Button
                    variant="secondary"
                    label="← Back"
                    onPress={() => navigation.goBack()}
                    style={{ alignSelf: "flex-start", paddingHorizontal: 12, paddingVertical: 8, height: 40 }}
                />
                <Text style={styles.title}>Settings</Text>
            </View>

            <Card style={{ marginBottom: 14 }}>
                <Text style={styles.cardTitle}>🖥  Backend Server URL</Text>
                <Text style={styles.hint}>
                    Use your computer's LAN IP when on the same Wi-Fi.
                </Text>
                <TextInput
                    style={styles.input}
                    value={serverUrl}
                    onChangeText={setServerUrl}
                    placeholder="http://192.168.1.100:8000"
                    placeholderTextColor={Colors.textSub}
                    autoCapitalize="none"
                    autoCorrect={false}
                    keyboardType="url"
                />
                <Button
                    variant="secondary"
                    label={scanning ? scanMsg : "🔍 Auto-Detect Server (mDNS)"}
                    onPress={handleScan}
                    loading={scanning}
                    style={{ marginBottom: 12, borderStyle: "dashed", borderWidth: 1, borderColor: Colors.primary }}
                />
                <View style={styles.btnRow}>
                    <Button
                        variant="secondary"
                        label={testing ? "Testing…" : "🔌 Test"}
                        loading={testing}
                        onPress={handleTest}
                        style={{ flex: 1 }}
                    />
                    <Button
                        variant="primary"
                        label="💾 Save"
                        onPress={handleSave}
                        style={{ flex: 2 }}
                    />
                </View>
                {status === "ok" && <Text style={{ color: Colors.success, marginTop: 8 }}>✅ Connected!</Text>}
                {status === "fail" && <Text style={{ color: Colors.error, marginTop: 8 }}>❌ Could not reach server.</Text>}
            </Card>

            <Card style={{ marginBottom: 14 }}>
                <Text style={styles.cardTitle}>⚙️  Preferences</Text>

                <Text style={styles.rowLabel}>Default Format</Text>
                <View style={styles.optionRow}>
                    <Button
                        variant={format === "mp3" ? "primary" : "secondary"}
                        label="MP3"
                        onPress={() => setFormat("mp3")}
                        style={StyleSheet.flatten([{ flex: 1 }, format !== "mp3" ? { borderColor: Colors.border, borderWidth: 1 } : {}]) as ViewStyle}
                    />
                    <Button
                        variant={format === "mp4" ? "primary" : "secondary"}
                        label="MP4"
                        onPress={() => setFormat("mp4")}
                        style={StyleSheet.flatten([{ flex: 1, marginLeft: 8 }, format !== "mp4" ? { borderColor: Colors.border, borderWidth: 1 } : {}]) as ViewStyle}
                    />
                </View>

                <Text style={[styles.rowLabel, { marginTop: 12 }]}>Audio Quality (MP3)</Text>
                <View style={styles.optionRow}>
                    {["128k", "192k", "256k", "320k"].map((q, idx) => (
                        <Button
                            key={q}
                            variant={quality === q ? "primary" : "secondary"}
                            label={q}
                            onPress={() => setQuality(q)}
                            style={StyleSheet.flatten([{ flex: 1, ...(idx > 0 ? { marginLeft: 8 } : {}) }, quality !== q ? { borderColor: Colors.border, borderWidth: 1 } : {}]) as ViewStyle}
                        />
                    ))}
                </View>
            </Card>

            <Card style={{ marginBottom: 14 }}>
                <Text style={styles.cardTitle}>🔐  Advanced (Optional)</Text>
                <Text style={styles.hint}>
                    Only needed if your backend requires an API key for public access.
                </Text>
                <TextInput
                    style={styles.input}
                    value={apiKey}
                    onChangeText={setApiKeyLocal}
                    placeholder="API Key"
                    placeholderTextColor={Colors.textSub}
                    secureTextEntry
                    autoCapitalize="none"
                    autoCorrect={false}
                />
            </Card>

            <Card style={{ marginBottom: 14 }}>
                <Text style={styles.cardTitle}>ℹ️  About</Text>
                <Text style={styles.infoRow}>App:       <Text style={styles.infoVal}>MediaGrab v{packageJson.version}</Text></Text>
                <Text style={styles.infoRow}>Publisher: <Text style={styles.infoVal}>Isaac Onyango</Text></Text>
                <Button
                    label="🔄 Check for Updates"
                    variant="secondary"
                    onPress={handleCheckUpdate}
                    style={{ marginTop: 12 }}
                />
            </Card>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    root: { flex: 1, backgroundColor: Colors.bg },
    scroll: { padding: 16, paddingBottom: 60 },
    header: { flexDirection: "row", alignItems: "center", marginBottom: 16, gap: 12 },
    title: { fontSize: 26, fontWeight: "800", color: Colors.text },

    cardTitle: { fontSize: 14, fontWeight: "700", color: Colors.text, marginBottom: 10 },
    hint: { fontSize: 12, color: Colors.textSub, marginBottom: 10, lineHeight: 18 },

    input: {
        backgroundColor: "#111", borderRadius: 10, padding: 12,
        fontSize: 13, color: Colors.text, borderWidth: 1, borderColor: "#2a2a2a", marginBottom: 12,
        fontFamily: "monospace",
    },

    btnRow: { flexDirection: "row", gap: 10 },

    rowLabel: { fontSize: 12, color: Colors.textSub, fontWeight: "600", marginBottom: 6, textTransform: "uppercase", letterSpacing: 0.5 },
    optionRow: { flexDirection: "row", justifyContent: "space-between" },

    infoRow: { fontSize: 13, color: Colors.textSub, marginBottom: 4 },
    infoVal: { color: Colors.text },
});
