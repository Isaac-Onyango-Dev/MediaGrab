/**
 * MediaGrab Mobile – Shared UI Components
 * Reusable across HomeScreen, DownloadScreen, SettingsScreen
 */

import React, { useEffect, useRef } from "react";
import {
  ActivityIndicator,
  Animated,
  Platform,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  ViewStyle,
} from "react-native";

// ─────────────────────────────────────────────
// Design Tokens
// ─────────────────────────────────────────────

export const Colors = {
  bg:       "#0f0f0f",
  card:     "#1a1a1a",
  border:   "#2a2a2a",
  primary:  "#3b82f6",
  success:  "#22c55e",
  warning:  "#f59e0b",
  error:    "#ef4444",
  text:     "#f1f5f9",
  textSub:  "#94a3b8",
  pill:     "#1e293b",
} as const;

export const Radii = { sm: 8, md: 12, lg: 16, full: 999 } as const;

// ─────────────────────────────────────────────
// Card
// ─────────────────────────────────────────────

interface CardProps {
  children: React.ReactNode;
  style?: ViewStyle;
}

export const Card = ({ children, style }: CardProps) => (
  <View style={[cardStyles.root, style]}>{children}</View>
);

const cardStyles = StyleSheet.create({
  root: {
    backgroundColor: Colors.card,
    borderRadius:    Radii.lg,
    padding:         16,
    marginBottom:    12,
    borderWidth:     1,
    borderColor:     Colors.border,
  },
});

// ─────────────────────────────────────────────
// Section Label
// ─────────────────────────────────────────────

export const SectionLabel = ({ text }: { text: string }) => (
  <Text style={slStyles.text}>{text}</Text>
);

const slStyles = StyleSheet.create({
  text: {
    fontSize:      11,
    color:         Colors.textSub,
    fontWeight:    "700",
    letterSpacing: 1,
    marginBottom:  8,
    marginTop:     4,
    textTransform: "uppercase",
  },
});

// ─────────────────────────────────────────────
// Primary Button
// ─────────────────────────────────────────────

interface BtnProps {
  label:     string;
  onPress:   () => void;
  loading?:  boolean;
  disabled?: boolean;
  style?:    ViewStyle;
  variant?:  "primary" | "secondary" | "danger";
}

export const Button = ({
  label, onPress, loading, disabled, style, variant = "primary",
}: BtnProps) => {
  const bg = variant === "primary"   ? Colors.primary
           : variant === "danger"    ? "#450a0a"
           : Colors.pill;

  const border = variant === "danger" ? Colors.error : "transparent";

  return (
    <TouchableOpacity
      style={[btnStyles.root, { backgroundColor: bg, borderColor: border }, style,
              (loading || disabled) && btnStyles.disabled]}
      onPress={onPress}
      disabled={loading || disabled}
      activeOpacity={0.75}
    >
      {loading
        ? <ActivityIndicator color="#fff" size="small" />
        : <Text style={[btnStyles.text, variant === "secondary" && { color: Colors.text }]}>
            {label}
          </Text>
      }
    </TouchableOpacity>
  );
};

const btnStyles = StyleSheet.create({
  root:     { borderRadius: Radii.md, padding: 14, alignItems: "center", borderWidth: 1 },
  text:     { color: "#fff", fontWeight: "700", fontSize: 15 },
  disabled: { opacity: 0.5 },
});

// ─────────────────────────────────────────────
// Chip (toggle selector)
// ─────────────────────────────────────────────

interface ChipProps {
  label:    string;
  selected: boolean;
  onPress:  () => void;
}

export const Chip = ({ label, selected, onPress }: ChipProps) => (
  <TouchableOpacity
    style={[chipStyles.root, selected && chipStyles.selected]}
    onPress={onPress}
    activeOpacity={0.75}
  >
    <Text style={[chipStyles.text, selected && chipStyles.textSelected]}>{label}</Text>
  </TouchableOpacity>
);

const chipStyles = StyleSheet.create({
  root:         { backgroundColor: Colors.pill, borderRadius: Radii.full, paddingHorizontal: 14, paddingVertical: 10, borderWidth: 1, borderColor: Colors.border },
  selected:     { backgroundColor: "#1d4ed8", borderColor: Colors.primary },
  text:         { color: Colors.textSub, fontSize: 14 },
  textSelected: { color: "#fff", fontWeight: "700" },
});

// ─────────────────────────────────────────────
// Platform Badge
// ─────────────────────────────────────────────

const PLATFORM_ICONS: Record<string, string> = {
  youtube:     "▶",
  tiktok:      "♪",
  instagram:   "◉",
  facebook:    "ƒ",
  twitter:     "𝕏",
  vimeo:       "V",
  reddit:      "R",
  dailymotion: "D",
  twitch:      "T",
  generic:     "🔗",
  generic_http:"🔗",
};

export const PlatformBadge = ({ platform }: { platform: string }) => (
  <View style={pbStyles.root}>
    <Text style={pbStyles.text}>
      {PLATFORM_ICONS[platform] ?? "🔗"}  {platform.charAt(0).toUpperCase() + platform.slice(1)}
    </Text>
  </View>
);

const pbStyles = StyleSheet.create({
  root: { alignSelf: "flex-start", backgroundColor: Colors.pill, borderRadius: Radii.full, paddingHorizontal: 10, paddingVertical: 4, marginBottom: 8 },
  text: { color: Colors.primary, fontSize: 12, fontWeight: "600" },
});

// ─────────────────────────────────────────────
// Animated Progress Bar
// ─────────────────────────────────────────────

export const ProgressBar = ({ progress }: { progress: number }) => {
  const anim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(anim, {
      toValue:         progress / 100,
      duration:        250,
      useNativeDriver: false,
    }).start();
  }, [progress]);

  const fillColor = anim.interpolate({
    inputRange:  [0, 0.99, 1],
    outputRange: [Colors.primary, Colors.primary, Colors.success],
  });

  return (
    <View style={pbarStyles.track}>
      <Animated.View
        style={[
          pbarStyles.fill,
          {
            width:           anim.interpolate({ inputRange: [0, 1], outputRange: ["0%", "100%"] }),
            backgroundColor: fillColor,
          },
        ]}
      />
    </View>
  );
};

const pbarStyles = StyleSheet.create({
  track: { height: 10, backgroundColor: "#222", borderRadius: 5, overflow: "hidden" },
  fill:  { height: "100%", borderRadius: 5 },
});

// ─────────────────────────────────────────────
// Status Banner
// ─────────────────────────────────────────────

type BannerKind = "info" | "success" | "warning" | "error";

const BANNER_COLORS: Record<BannerKind, { bg: string; border: string; text: string }> = {
  info:    { bg: "#0c1a2e", border: Colors.primary, text: Colors.primary },
  success: { bg: "#052e16", border: Colors.success, text: Colors.success },
  warning: { bg: "#1c1000", border: Colors.warning, text: Colors.warning },
  error:   { bg: "#1c0000", border: Colors.error,   text: Colors.error   },
};

interface BannerProps {
  message: string;
  kind:    BannerKind;
  onPress?: () => void;
}

export const Banner = ({ message, kind, onPress }: BannerProps) => {
  const { bg, border, text } = BANNER_COLORS[kind];
  return (
    <TouchableOpacity
      style={[banStyles.root, { backgroundColor: bg, borderColor: border }]}
      onPress={onPress}
      disabled={!onPress}
      activeOpacity={onPress ? 0.75 : 1}
    >
      <Text style={[banStyles.text, { color: text }]}>{message}</Text>
    </TouchableOpacity>
  );
};

const banStyles = StyleSheet.create({
  root: { borderRadius: Radii.md, padding: 12, marginBottom: 12, borderWidth: 1 },
  text: { fontSize: 13, textAlign: "center", fontWeight: "600" },
});

// ─────────────────────────────────────────────
// Divider
// ─────────────────────────────────────────────

export const Divider = ({ style }: { style?: ViewStyle }) => (
  <View style={[{ height: 1, backgroundColor: Colors.border, marginVertical: 10 }, style]} />
);

// ─────────────────────────────────────────────
// Monospace Code Block
// ─────────────────────────────────────────────

export const CodeBlock = ({ children }: { children: string }) => (
  <View style={codeStyles.root}>
    <Text style={codeStyles.text}>{children}</Text>
  </View>
);

const codeStyles = StyleSheet.create({
  root: { backgroundColor: "#111", borderRadius: Radii.sm, padding: 12, marginBottom: 8 },
  text: {
    fontFamily: Platform.OS === "android" ? "monospace" : "Menlo",
    fontSize:   12,
    color:      "#a3e635",
    lineHeight: 20,
  },
});
