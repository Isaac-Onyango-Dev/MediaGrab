/**
 * MediaGrab Mobile – Root App
 * Stack Navigator: Home → Download → Settings
 */

import React from "react";
import { StatusBar } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { SafeAreaProvider } from "react-native-safe-area-context";

import HomeScreen     from "./src/screens/HomeScreen";
import DownloadScreen from "./src/screens/DownloadScreen";
import SettingsScreen from "./src/screens/SettingsScreen";

const Stack = createNativeStackNavigator();

export default function App() {
  return (
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
          <Stack.Screen name="Download" component={DownloadScreen as any} />
          <Stack.Screen name="Settings" component={SettingsScreen} />
        </Stack.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
