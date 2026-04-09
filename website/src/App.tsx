import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Download, Zap, Shield, ChevronRight, Share2, Heart, Copy, Check, Music, List, Activity, FolderOpen, Globe, type LucideIcon } from 'lucide-react';

import {
  FaWindows, FaApple, FaLinux, FaAndroid, FaGithub,
  FaXTwitter, FaReddit, FaWhatsapp, FaFacebookF,
  FaLinkedinIn, FaTelegram, FaMastodon, FaHackerNews, FaPinterestP
} from 'react-icons/fa6';
import { SiThreads } from 'react-icons/si';

import DonationModal from './components/DonationModal';

/**
 * Background Pellets - Floating Gaussian Blur Orbs
 */
const BackgroundPellets: React.FC = () => {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
      <motion.div
        animate={{ x: [0, 50, 0], y: [0, 80, 0] }}
        transition={{ duration: 25, repeat: Infinity, ease: "easeInOut" }}
        className="blur-orb w-[600px] h-[600px] bg-brand-vivid -top-40 -left-40 opacity-40"
      />
      <motion.div
        animate={{ x: [0, -40, 0], y: [0, 60, 0] }}
        transition={{ duration: 30, repeat: Infinity, ease: "easeInOut" }}
        className="blur-orb w-[500px] h-[500px] bg-brand-electric -bottom-20 -right-20 opacity-30"
      />
      <motion.div
        animate={{ x: [0, 30, 0], y: [0, -50, 0] }}
        transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
        className="blur-orb w-[400px] h-[400px] bg-brand-violet top-1/2 left-1/4 opacity-20"
      />
    </div>
  );
};

interface FeatureCardProps {
  icon: LucideIcon;
  title: string;
  desc: string;
}

const FeatureCard: React.FC<FeatureCardProps> = ({ icon: Icon, title, desc }) => (
  <motion.div
    whileHover={{ y: -8 }}
    className="glass-card glass-card-hover p-8 rounded-3xl"
  >
    <div className="w-14 h-14 rounded-2xl bg-brand-electric/20 flex items-center justify-center mb-6 border border-brand-electric/30">
      <Icon size={28} className="text-brand-electric" />
    </div>
    <h3 className="text-xl font-bold mb-3 text-white">{title}</h3>
    <p className="text-white/80 text-sm leading-relaxed">{desc}</p>
  </motion.div>
);

// PlatformCard component removed to resolve unused variable warning as manual cards are used below.


export default function App() {
  const [isDonationModalOpen, setIsDonationModalOpen] = useState(false);
  const [copied, setCopied] = useState<'link' | 'msg' | null>(null);

  const handleCopy = (type: 'link' | 'msg') => {
    const text = type === 'link' ? window.location.href : "Extract Media easily with MediaGrab! Check it out at: " + window.location.href;
    navigator.clipboard.writeText(text);
    setCopied(type);
    setTimeout(() => setCopied(null), 2000);
  };

  const [downloadInfo] = useState(() => {
    const ua = typeof window !== 'undefined' ? window.navigator.userAgent.toLowerCase() : '';
    const releaseBase = "https://github.com/Isaac-Onyango-Dev/MediaGrab/releases/download/v1.0.0/";

    if (ua.includes("win")) {
      return { label: "Download for Windows", link: `${releaseBase}MediaGrab-1.0.0-Setup.exe` };
    } else if (ua.includes("mac")) {
      return { label: "Download for macOS", link: `${releaseBase}MediaGrab-macOS.dmg` };
    } else if (ua.includes("android")) {
      return { label: "Download for Android", link: `${releaseBase}MediaGrab-Android.apk` };
    } else if (ua.includes("linux")) {
      return { label: "Download for Linux", link: `${releaseBase}MediaGrab-Linux` };
    }

    return { label: "View All Downloads", link: "https://github.com/Isaac-Onyango-Dev/MediaGrab/releases" };
  });

  const shareIcons = [
    { icon: FaXTwitter, name: "X (Twitter)", color: "bg-black" },
    { icon: FaReddit, name: "Reddit", color: "bg-[#FF4500]" },
    { icon: FaWhatsapp, name: "WhatsApp", color: "bg-[#25D366]" },
    { icon: FaFacebookF, name: "Facebook", color: "bg-[#1877F2]" },
    { icon: FaLinkedinIn, name: "LinkedIn", color: "bg-[#0A66C2]" },
    { icon: FaTelegram, name: "Telegram", color: "bg-[#24A1DE]" },
    { icon: SiThreads, name: "Threads", color: "bg-black" },
    { icon: FaMastodon, name: "Mastodon", color: "bg-[#6364FF]" },
    { icon: FaHackerNews, name: "Hacker News", color: "bg-[#FF6600]" },
    { icon: FaPinterestP, name: "Pinterest", color: "bg-[#E60023]" },
  ];

  const logoUrl = `${import.meta.env.BASE_URL}logo.png`;

  return (
    <div className="relative min-h-screen bg-brand-950 bg-gradient-premium selection:bg-brand-electric/30">
      <BackgroundPellets />
      <DonationModal isOpen={isDonationModalOpen} onClose={() => setIsDonationModalOpen(false)} />

      {/* Nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 px-6 py-6 border-b border-white/5 backdrop-blur-md bg-transparent">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-electric/20 border border-brand-electric/30 p-1.5 backdrop-blur-xl shrink-0">
              <img src={logoUrl} alt="Logo" className="w-full h-full object-contain" onError={(e) => {
                e.currentTarget.style.display = 'none';
              }} />
            </div>
            <span className="text-xl font-black tracking-tighter text-white">MediaGrab</span>
          </div>
          <a href="https://github.com/Isaac-Onyango-Dev/MediaGrab" className="flex items-center gap-2 text-sm font-medium text-white hover:text-brand-electric transition-colors">
            <FaGithub size={20} />
            <span className="hidden sm:inline">GitHub Repository</span>
          </a>
        </div>
      </nav>

      {/* Hero */}
      <main className="relative z-10 pt-20 pb-20 px-6">
        <section className="max-w-96 mx-auto text-center py-20">
          {/* App Icon */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="w-16 h-16 mx-auto mb-8 rounded-lg bg-blue-700 flex items-center justify-center"
          >
            <span className="text-white text-4xl font-bold">M</span>
          </motion.div>

          {/* App Name */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-5xl font-bold text-white mb-3"
          >
            MediaGrab
          </motion.h1>

          {/* Tagline */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="text-xl text-slate-400 mb-8"
          >
            Download videos and audio from anywhere. Free. No limits.
          </motion.p>

          {/* Platform Pills */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="flex flex-wrap gap-2 justify-center mb-12"
          >
            {['YouTube', 'YouTube Music', 'TikTok', 'Instagram', 'Facebook', 'Twitter/X', 'Vimeo', 'Reddit', 'Twitch', 'Dailymotion', 'and more'].map((platform, idx) => (
              <span key={idx} className="px-3 py-1.5 text-xs font-medium rounded-full bg-slate-900 border border-slate-700 text-slate-400">
                {platform}
              </span>
            ))}
          </motion.div>

          {/* Primary CTA Button */}
          <motion.a
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            href={downloadInfo.link}
            className="inline-flex items-center gap-2 px-7 py-3 rounded-xl bg-blue-500 text-white font-bold text-base hover:bg-blue-600 transition-all mb-6 group"
          >
            <Download size={20} className="group-hover:translate-y-0.5 transition-transform" />
            {downloadInfo.label}
          </motion.a>

          {/* Secondary Link */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            <a href="#downloads" className="text-slate-400 hover:text-white transition-colors text-sm font-medium">
              View all downloads ↓
            </a>
          </motion.div>
        </section>

        {/* Everything You Need */}
        <section className="max-w-7xl mx-auto py-32 border-t border-white/5 mt-20 px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-white mb-3">Everything you need</h2>
            <p className="text-slate-400">All the features to download media the way you want</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              { icon: Globe, title: "10+ Platforms", desc: "YouTube, TikTok, Instagram, Vimeo, and dozens more supported by yt-dlp engines." },
              { icon: Music, title: "MP3 & MP4", desc: "Download as lossy audio-only MP3 or full-quality MP4 video with ease." },
              { icon: List, title: "Playlist Selection", desc: "Pick individual videos from any playlist — no forced bulk downloads or slow waiting." },
              { icon: Activity, title: "Real-time Progress", desc: "Live speed indicators, ETA, and per-item progress for every ongoing download." },
              { icon: FolderOpen, title: "Smart Folders", desc: "Playlists get their own named subfolder, automatically organised for your library." },
              { icon: Shield, title: "100% Free", desc: "No subscriptions, no accounts, no limits. Fully open source on GitHub forever." }
            ].map((feature, idx) => (
              <FeatureCard
                key={idx}
                icon={feature.icon}
                title={feature.title}
                desc={feature.desc}
              />
            ))}
          </div>
        </section>

        {/* Downloads Section */}
        <section id="downloads" className="max-w-7xl mx-auto py-32 mt-20 border-t border-white/5 px-6">
          <div className="text-center mb-16">
            <h2 className="text-5xl font-bold text-white mb-2">Choose your platform</h2>
            <p className="text-slate-400">Download MediaGrab for your device. Fast, free, and no limits.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Windows Card */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className={`relative bg-slate-900 border rounded-xl p-6 transition-all hover:transform hover:scale-101 group ${downloadInfo.label.includes("Windows") ? "border-blue-500" : "border-slate-700"
                }`}
            >
              {downloadInfo.label.includes("Windows") && (
                <div className="absolute top-3 right-3 bg-blue-700 text-white text-xs font-semibold px-2 py-1 rounded-full">
                  Recommended
                </div>
              )}
              <div className="w-14 h-14 rounded-full bg-blue-600 flex items-center justify-center mb-4">
                <FaWindows size={28} className="text-white" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-1">Windows</h3>
              <p className="text-sm text-slate-500 mb-3">Windows 10 / 11 · 64-bit</p>
              <span className="inline-block text-xs bg-slate-800 text-slate-400 px-2 py-1 rounded mb-4">.exe · ~75 MB</span>
              <a
                href="https://github.com/Isaac-Onyango-Dev/MediaGrab/releases/download/v1.0.0/MediaGrab-1.0.0-Setup.exe"
                className="block w-full bg-blue-500 text-white text-sm font-semibold py-2.5 rounded text-center hover:bg-blue-600 transition-all mb-2"
              >
                Download for Windows
              </a>
              <p className="text-xs text-slate-500 italic">Requires FFmpeg — <code className="text-slate-400">winget install ffmpeg</code></p>
            </motion.div>

            {/* macOS Card */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.05 }}
              className={`relative bg-slate-900 border rounded-xl p-6 transition-all hover:transform hover:scale-101 group ${downloadInfo.label.includes("macOS") ? "border-blue-500" : "border-slate-700"
                }`}
            >
              {downloadInfo.label.includes("macOS") && (
                <div className="absolute top-3 right-3 bg-blue-700 text-white text-xs font-semibold px-2 py-1 rounded-full">
                  Recommended
                </div>
              )}
              <div className="w-14 h-14 rounded-full bg-slate-700 flex items-center justify-center mb-4">
                <FaApple size={28} className="text-white" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-1">macOS</h3>
              <p className="text-sm text-slate-500 mb-3">macOS 11 Big Sur and later</p>
              <span className="inline-block text-xs bg-slate-800 text-slate-400 px-2 py-1 rounded mb-4">.dmg · ~80 MB</span>
              <a
                href="https://github.com/Isaac-Onyango-Dev/MediaGrab/releases/download/v1.0.0/MediaGrab-macOS.dmg"
                className="block w-full bg-blue-500 text-white text-sm font-semibold py-2.5 rounded text-center hover:bg-blue-600 transition-all mb-2"
              >
                Download for macOS
              </a>
              <p className="text-xs text-slate-500 italic">Requires FFmpeg — <code className="text-slate-400">brew install ffmpeg</code></p>
            </motion.div>

            {/* Linux Card */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 }}
              className={`relative bg-slate-900 border rounded-xl p-6 transition-all hover:transform hover:scale-101 group ${downloadInfo.label.includes("Linux") ? "border-blue-500" : "border-slate-700"
                }`}
            >
              {downloadInfo.label.includes("Linux") && (
                <div className="absolute top-3 right-3 bg-blue-700 text-white text-xs font-semibold px-2 py-1 rounded-full">
                  Recommended
                </div>
              )}
              <div className="w-14 h-14 rounded-full bg-orange-500 flex items-center justify-center mb-4">
                <FaLinux size={28} className="text-white" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-1">Linux</h3>
              <p className="text-sm text-slate-500 mb-3">Ubuntu 20.04 · Debian · Fedora</p>
              <span className="inline-block text-xs bg-slate-800 text-slate-400 px-2 py-1 rounded mb-4">binary · ~65 MB</span>
              <a
                href="https://github.com/Isaac-Onyango-Dev/MediaGrab/releases/download/v1.0.0/MediaGrab-Linux"
                className="block w-full bg-blue-500 text-white text-sm font-semibold py-2.5 rounded text-center hover:bg-blue-600 transition-all mb-2"
              >
                Download for Linux
              </a>
              <p className="text-xs text-slate-500 italic">Requires FFmpeg — <code className="text-slate-400">sudo apt install ffmpeg</code></p>
            </motion.div>

            {/* Android Card */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.15 }}
              className={`relative bg-slate-900 border rounded-xl p-6 transition-all hover:transform hover:scale-101 group ${downloadInfo.label.includes("Android") ? "border-blue-500" : "border-slate-700"
                }`}
            >
              {downloadInfo.label.includes("Android") && (
                <div className="absolute top-3 right-3 bg-blue-700 text-white text-xs font-semibold px-2 py-1 rounded-full">
                  Recommended
                </div>
              )}
              <div className="w-14 h-14 rounded-full bg-green-500 flex items-center justify-center mb-4">
                <FaAndroid size={28} className="text-white" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-1">Android</h3>
              <p className="text-sm text-slate-500 mb-3">Android 7.0 (API 24) and later</p>
              <span className="inline-block text-xs bg-slate-800 text-slate-400 px-2 py-1 rounded mb-4">.apk · sideload</span>
              <a
                href="https://github.com/Isaac-Onyango-Dev/MediaGrab/releases/download/v1.0.0/MediaGrab-Android.apk"
                className="block w-full bg-blue-500 text-white text-sm font-semibold py-2.5 rounded text-center hover:bg-blue-600 transition-all mb-2"
              >
                Download APK
              </a>
              <p className="text-xs text-slate-500 italic">Enable "Install unknown apps" in Android Settings</p>
            </motion.div>
          </div>
        </section>

        {/* Get Started Section */}
        <section className="max-w-7xl mx-auto py-32 mt-20 border-t border-white/5 px-6">
          <div className="text-center mb-20">
            <h2 className="text-4xl font-bold text-white mb-3">Get started in 3 steps</h2>
            <p className="text-slate-400">Download and extract media in minutes</p>
          </div>

          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Step 1 */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                className="text-center"
              >
                <div className="w-12 h-12 rounded-full bg-blue-700 text-white flex items-center justify-center text-lg font-bold mx-auto mb-4">
                  1
                </div>
                <h3 className="text-base font-semibold text-white mb-2">Download & Install</h3>
                <p className="text-sm text-slate-500 leading-relaxed">Get the app for your platform above. No Python or Node.js required.</p>
              </motion.div>

              {/* Step 2 */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.1 }}
                className="text-center"
              >
                <div className="w-12 h-12 rounded-full bg-blue-700 text-white flex items-center justify-center text-lg font-bold mx-auto mb-4">
                  2
                </div>
                <h3 className="text-base font-semibold text-white mb-2">Paste Any URL</h3>
                <p className="text-sm text-slate-500 leading-relaxed">Copy a video or playlist link from YouTube, TikTok, Instagram, or any supported site.</p>
              </motion.div>

              {/* Step 3 */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.2 }}
                className="text-center"
              >
                <div className="w-12 h-12 rounded-full bg-blue-700 text-white flex items-center justify-center text-lg font-bold mx-auto mb-4">
                  3
                </div>
                <h3 className="text-base font-semibold text-white mb-2">Choose & Download</h3>
                <p className="text-sm text-slate-500 leading-relaxed">Pick MP3 or MP4, select your quality, choose which playlist videos you want, then hit download.</p>
              </motion.div>
            </div>
          </div>
        </section>

        {/* Support & Community Section */}
        <section className="max-w-7xl mx-auto py-32 mt-20 border-t border-white/5">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">

            {/* Share Grid */}
            <div className="lg:col-span-2">
              <h3 className="text-white text-xs font-bold uppercase tracking-[0.3em] mb-8 opacity-50">Share on a Platform</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {shareIcons.map((platform, idx) => (
                  <motion.a
                    key={idx}
                    href={(() => {
                      const url = encodeURIComponent(window.location.href);
                      const text = encodeURIComponent("Extract Media easily with MediaGrab! Check it out: " + window.location.href);
                      switch (platform.name) {
                        case "X (Twitter)": return `https://twitter.com/intent/tweet?text=${text}&url=${url}`;
                        case "Reddit": return `https://reddit.com/submit?url=${url}&title=${text}`;
                        case "WhatsApp": return `https://wa.me/?text=${text}%20${url}`;
                        case "Facebook": return `https://www.facebook.com/sharer/sharer.php?u=${url}`;
                        case "LinkedIn": return `https://www.linkedin.com/sharing/share-offsite/?url=${url}`;
                        case "Telegram": return `https://t.me/share/url?url=${url}&text=${text}`;
                        case "Threads": return `https://threads.net/intent/post?text=${text}&url=${url}`;
                        case "Mastodon": return `https://mastodon.social/share?text=${text}&url=${url}`;
                        case "Hacker News": return `https://news.ycombinator.com/submitlink?u=${url}&t=${text}`;
                        case "Pinterest": return `https://pinterest.com/pin/create/button/?url=${url}&description=${text}`;
                        default: return "#";
                      }
                    })()}
                    target="_blank"
                    rel="noopener noreferrer"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className={`flex items-center gap-4 p-4 rounded-xl ${platform.color} glass-card border-none hover:brightness-125 transition-all text-white font-bold text-left group`}
                  >
                    <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center shrink-0">
                      <platform.icon size={20} />
                    </div>
                    <span className="text-sm truncate">{platform.name}</span>
                    <Share2 size={16} className="ml-auto opacity-0 group-hover:opacity-100 transition-opacity" />
                  </motion.a>
                ))}
              </div>

              <div className="mt-8 flex flex-col gap-3">
                <h3 className="text-white text-xs font-bold uppercase tracking-[0.3em] mb-2 opacity-50">Copy to Clipboard</h3>
                <button
                  onClick={() => handleCopy('link')}
                  className="w-full p-5 rounded-2xl glass-card text-white flex items-center gap-4 hover:bg-white/5 transition-all group border-white/10"
                >
                  <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center border border-white/10">
                    {copied === 'link' ? <Check className="text-green-400" size={20} /> : <Copy size={20} />}
                  </div>
                  <span className="font-bold">Copy App Link</span>
                  {copied === 'link' && <span className="ml-auto text-xs text-green-400 font-bold uppercase">Copied!</span>}
                </button>
                <button
                  onClick={() => handleCopy('msg')}
                  className="w-full p-5 rounded-2xl glass-card text-white flex items-center gap-4 hover:bg-white/5 transition-all group border-white/10"
                >
                  <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center border border-white/10">
                    {copied === 'msg' ? <Check className="text-green-400" size={20} /> : <Share2 size={20} />}
                  </div>
                  <span className="font-bold">Copy Share Message</span>
                  {copied === 'msg' && <span className="ml-auto text-xs text-green-400 font-bold uppercase">Copied!</span>}
                </button>
              </div>
            </div>

            {/* Donation Card */}
            <div>
              <h3 className="text-white text-xs font-bold uppercase tracking-[0.3em] mb-8 opacity-50">Support Project</h3>
              <div className="glass-card p-10 rounded-3xl border-brand-electric/30 flex flex-col h-full bg-gradient-to-br from-brand-electric/10 to-transparent">
                <div className="w-16 h-16 rounded-2xl bg-brand-electric/20 border border-brand-electric/30 flex items-center justify-center mb-8">
                  <Heart className="text-brand-electric fill-brand-electric/20" size={32} />
                </div>
                <h4 className="text-3xl font-black text-white tracking-tighter mb-4 leading-tight">Help us keep MediaGrab free forever.</h4>
                <p className="text-white mb-10 leading-relaxed font-medium">
                  MediaGrab is an open-source project driven by the community. Your support helps us cover server costs and keep the project alive.
                </p>
                <button
                  onClick={() => setIsDonationModalOpen(true)}
                  className="mt-auto w-full py-5 rounded-2xl bg-white text-black font-black text-lg hover:bg-slate-200 transition-all flex items-center justify-center gap-3"
                >
                  Support Development
                  <Zap size={20} className="fill-black" />
                </button>
              </div>
            </div>

          </div>
        </section>

        {/* GitHub CTA */}
        <section className="max-w-7xl mx-auto pb-32">
          <div className="glass-card p-8 rounded-3xl flex flex-col md:flex-row items-center justify-between gap-8 border-white/10">
            <div className="flex items-center gap-6">
              <div className="w-16 h-16 rounded-2xl bg-brand-vivid/20 border border-brand-vivid/30 flex items-center justify-center">
                <FaGithub className="text-brand-vivid" size={32} />
              </div>
              <div>
                <h3 className="text-2xl font-black text-white leading-tight">Public Domain Source</h3>
                <p className="text-white text-sm opacity-80">Auditable code. Community driven. Absolutely free.</p>
              </div>
            </div>
            <a
              href="https://github.com/Isaac-Onyango-Dev/MediaGrab"
              target="_blank"
              className="w-full md:w-auto px-8 py-4 rounded-xl bg-white text-black font-black flex items-center justify-center gap-2 hover:bg-slate-200 transition-colors"
            >
              Stars on GitHub
              <ChevronRight size={20} />
            </a>
          </div>
        </section>
      </main>

      <footer className="relative z-10 py-16 px-6 border-t border-slate-800">
        <div className="max-w-7xl mx-auto text-center">
          {/* Row 1: App name + tagline */}
          <div className="mb-8">
            <h3 className="text-base font-semibold text-white mb-1">MediaGrab</h3>
            <p className="text-sm text-slate-500">Universal video downloader for Windows, macOS, Linux, and Android</p>
          </div>

          {/* Row 2: Navigation links */}
          <div className="flex flex-wrap justify-center gap-6 mb-8">
            <a href="https://github.com/Isaac-Onyango-Dev/MediaGrab" className="text-sm text-slate-500 hover:text-blue-500 transition-colors">
              GitHub Repo
            </a>
            <a href="https://github.com/Isaac-Onyango-Dev/MediaGrab/releases" className="text-sm text-slate-500 hover:text-blue-500 transition-colors">
              Releases
            </a>
            <a href="https://github.com/Isaac-Onyango-Dev/MediaGrab/issues" className="text-sm text-slate-500 hover:text-blue-500 transition-colors">
              Report Issue
            </a>
          </div>

          {/* Row 3: Attribution */}
          <p className="text-xs text-slate-600">Built with yt-dlp + FFmpeg · Open source · MIT License</p>
        </div>
      </footer>
    </div>
  );
}

