module.exports = function (api) {
  api.cache(true);
  return {
    presets: ["babel-preset-expo"],
    plugins: [
      // Optional: uncomment if you add react-native-reanimated later
      // "react-native-reanimated/plugin",
    ],
  };
};
