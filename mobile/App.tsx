/**
 * MediaGrab Mobile – Root App (v1.0.0 Production)
 * Stack Navigator: Home → Download → Settings
 * 
 * v1.0.0: Added Error Boundary to prevent full app crashes
 */

import React from "react";
import { StatusBar, View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { SafeAreaProvider } from "react-native-safe-area-context";

import HomeScreen     from "./src/screens/HomeScreen";
import DownloadScreen from "./src/screens/DownloadScreen";
import SettingsScreen from "./src/screens/SettingsScreen";

const Stack = createNativeStackNavigator();

// Error Boundary Component - prevents entire app from crashing
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("[MediaGrab] Unhandled Error:", error, errorInfo.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <View style={styles.errorContainer}>
          <Text style={styles.errorIcon}>⚠️</Text>
          <Text style={styles.errorTitle}>Something went wrong</Text>
          <Text style={styles.errorText}>
            MediaGrab encountered an unexpected error.
          </Text>
          <TouchableOpacity
            style={styles.retryButton}
            onPress={() => this.setState({ hasError: false })}
          >
            <Text style={styles.retryButtonText}>Try Again</Text>
          </TouchableOpacity>
        </View>
      );
    }

    return this.props.children;
  }
}

const styles = StyleSheet.create({
  errorContainer: {
    flex: 1,
    backgroundColor: "#0f0f0f",
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
  },
  errorIcon: {
    fontSize: 64,
    marginBottom: 16,
  },
  errorTitle: {
    fontSize: 22,
    fontWeight: "bold",
    color: "#ef4444",
    marginBottom: 8,
  },
  errorText: {
    fontSize: 16,
    color: "#94a3b8",
    textAlign: "center",
    marginBottom: 24,
  },
  retryButton: {
    backgroundColor: "#3b82f6",
    paddingVertical: 12,
    paddingHorizontal: 32,
    borderRadius: 8,
  },
  retryButtonText: {
    color: "#ffffff",
    fontSize: 16,
    fontWeight: "600",
  },
});

export default function App() {
  return (
    <ErrorBoundary>
      <SafeAreaProvider>
        <StatusBar barStyle="light-content" backgroundColor="#0f0f0f" />
        <NavigationContainer>
          <Stack.Navigator
            screenOptions={{
              headerShown:        false,
              contentStyle:       { backgroundColor: "#0f0f0f" },
              animation:          "slide_from_right",
            }}
          >
            <Stack.Screen name="Home"     component={HomeScreen}     />
            <Stack.Screen name="Download" component={DownloadScreen as React.ComponentType<any>} />
            <Stack.Screen name="Settings" component={SettingsScreen} />
          </Stack.Navigator>
        </NavigationContainer>
      </SafeAreaProvider>
    </ErrorBoundary>
  );
}
