const { getDefaultConfig } = require("expo/metro-config");

/** @type {import('expo/metro-config').MetroConfig} */
const config = getDefaultConfig(__dirname);

// Support additional asset extensions if needed
config.resolver.assetExts.push("db", "mp3", "ttf", "obj", "png", "jpg");

module.exports = config;
