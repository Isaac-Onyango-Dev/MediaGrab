import { useEffect, useState } from 'react';
import { Check, Copy, Download, FolderOpen, Gauge, Globe, Heart, ListChecks, Music, Share2 } from 'lucide-react';
import {
  FaAndroid, FaApple, FaFacebookF, FaGithub, FaHackerNews, FaLinkedinIn, FaLinux,
  FaMastodon, FaPinterestP, FaReddit, FaTelegram, FaWhatsapp, FaWindows, FaXTwitter,
} from 'react-icons/fa6';
import { SiThreads } from 'react-icons/si';

import ClawMachine from './components/ClawMachine';
import DonationModal from './components/DonationModal';
import Logo from './components/Logo';

// Release asset names come from .github/workflows/release.yml. APP_VERSION is
// injected from the repo VERSION file at build time, so a version bump does not
// leave the site pointing at assets that no longer exist.
const APP_VERSION = __APP_VERSION__;
const REPO = 'https://github.com/Isaac-Onyango-Dev/MediaGrab';
const RELEASE_BASE = `${REPO}/releases/download/v${APP_VERSION}/`;
const ALL_RELEASES = `${REPO}/releases`;
const CHANGELOG = `${REPO}/blob/main/CHANGELOG.md`;

const DOWNLOADS = {
  windows: `${RELEASE_BASE}MediaGrab-${APP_VERSION}-Setup.exe`,
  macos: `${RELEASE_BASE}MediaGrab-macOS.dmg`,
  linux: `${RELEASE_BASE}MediaGrab-${APP_VERSION}-x86_64.AppImage`,
  linuxTarball: `${RELEASE_BASE}MediaGrab-linux-x86_64.tar.gz`,
  android: `${RELEASE_BASE}MediaGrab-Android.apk`,
};

const SERVERS = [
  { name: 'Windows', href: `${RELEASE_BASE}MediaGrab-Server-Windows.exe` },
  { name: 'macOS', href: `${RELEASE_BASE}MediaGrab-Server-macOS` },
  { name: 'Linux', href: `${RELEASE_BASE}MediaGrab-Server-Linux` },
];

type OsKey = 'windows' | 'macos' | 'linux' | 'android';

const PLATFORMS: {
  key: OsKey;
  name: string;
  icon: typeof FaWindows;
  requirement: string;
  file: string;
  size: string;
  href: string;
  extra?: { label: string; href: string };
}[] = [
  {
    key: 'windows',
    name: 'Windows',
    icon: FaWindows,
    requirement: 'Windows 10 or 11, 64-bit. FFmpeg installs itself on first run.',
    file: `MediaGrab-${APP_VERSION}-Setup.exe`,
    size: 'about 75 MB',
    href: DOWNLOADS.windows,
  },
  {
    key: 'macos',
    name: 'macOS',
    icon: FaApple,
    requirement: 'macOS 11 Big Sur or later. Needs FFmpeg: brew install ffmpeg',
    file: 'MediaGrab-macOS.dmg',
    size: 'about 80 MB',
    href: DOWNLOADS.macos,
  },
  {
    key: 'linux',
    name: 'Linux',
    icon: FaLinux,
    requirement: 'x86_64 Ubuntu, Debian or Fedora. Needs FFmpeg: sudo apt install ffmpeg',
    file: `MediaGrab-${APP_VERSION}-x86_64.AppImage`,
    size: 'about 65 MB',
    href: DOWNLOADS.linux,
    extra: { label: 'Prefer a .tar.gz?', href: DOWNLOADS.linuxTarball },
  },
  {
    key: 'android',
    name: 'Android',
    icon: FaAndroid,
    requirement: 'Android 7.0 or later. Works as a remote for MediaGrab Server.',
    file: 'MediaGrab-Android.apk',
    size: 'install from file',
    href: DOWNLOADS.android,
  },
];

const FEATURES = [
  { icon: Globe, title: 'The sites you use', body: 'YouTube, TikTok, Instagram, X, Vimeo, Reddit, Twitch, Facebook and Dailymotion, plus direct links to any video file.' },
  { icon: Music, title: 'Video or just the sound', body: 'Save an MP4 at the quality you pick, or pull the audio out as an MP3.' },
  { icon: ListChecks, title: 'Only the videos you want', body: 'Paste a playlist and untick what you don’t need before anything downloads.' },
  { icon: FolderOpen, title: 'Tidy folders', body: 'Each playlist gets its own folder, named after the playlist.' },
  { icon: Gauge, title: 'Progress you can read', body: 'Live speed, time left, and which item of the playlist is downloading now.' },
  { icon: Heart, title: 'Free, with no account', body: 'No sign-up and no ads. The code is open on GitHub.' },
];

const HIGHLIGHTS = [
  { title: 'Downloads start, and progress moves', body: 'In 1.0.0 starting a download failed and the progress bar sat at zero. Both work now.' },
  { title: 'Playlist picking does what it says', body: 'The Android app downloads exactly the videos you ticked, and a single video no longer drags its whole playlist along.' },
  { title: 'Your other files are safe', body: 'Cancelling a download could delete unrelated files in the same folder. It now only removes its own leftovers.' },
];

const SHARE = [
  { icon: FaXTwitter, name: 'X', url: (u: string, t: string) => `https://twitter.com/intent/tweet?text=${t}&url=${u}` },
  { icon: FaReddit, name: 'Reddit', url: (u: string, t: string) => `https://reddit.com/submit?url=${u}&title=${t}` },
  { icon: FaWhatsapp, name: 'WhatsApp', url: (u: string, t: string) => `https://wa.me/?text=${t}%20${u}` },
  { icon: FaFacebookF, name: 'Facebook', url: (u: string) => `https://www.facebook.com/sharer/sharer.php?u=${u}` },
  { icon: FaLinkedinIn, name: 'LinkedIn', url: (u: string) => `https://www.linkedin.com/sharing/share-offsite/?url=${u}` },
  { icon: FaTelegram, name: 'Telegram', url: (u: string, t: string) => `https://t.me/share/url?url=${u}&text=${t}` },
  { icon: SiThreads, name: 'Threads', url: (u: string, t: string) => `https://threads.net/intent/post?text=${t}&url=${u}` },
  { icon: FaMastodon, name: 'Mastodon', url: (u: string, t: string) => `https://mastodon.social/share?text=${t}&url=${u}` },
  { icon: FaHackerNews, name: 'Hacker News', url: (u: string, t: string) => `https://news.ycombinator.com/submitlink?u=${u}&t=${t}` },
  { icon: FaPinterestP, name: 'Pinterest', url: (u: string, t: string) => `https://pinterest.com/pin/create/button/?url=${u}&description=${t}` },
];

const SHARE_TEXT = 'MediaGrab saves videos and audio from YouTube, TikTok and more. Free, no account.';

function detectOs(): OsKey | null {
  if (typeof navigator === 'undefined') return null;
  const ua = navigator.userAgent.toLowerCase();
  // Android before Linux: Android user agents contain "linux" too.
  if (ua.includes('android')) return 'android';
  if (ua.includes('win')) return 'windows';
  if (ua.includes('mac')) return 'macos';
  if (ua.includes('linux')) return 'linux';
  return null;
}

interface GhRelease {
  tag_name: string;
  published_at: string;
  draft: boolean;
  prerelease: boolean;
  assets: { download_count: number }[];
}

/** Latest release date and lifetime download count, straight from GitHub. */
function useReleaseStats() {
  const [stats, setStats] = useState<{ version: string; date: string; downloads: number } | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    fetch('https://api.github.com/repos/Isaac-Onyango-Dev/MediaGrab/releases?per_page=100', { signal: ctrl.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((releases: GhRelease[]) => {
        const published = releases.filter((r) => !r.draft);
        const latest = published.find((r) => !r.prerelease);
        if (!latest) return;
        const downloads = published.reduce(
          (sum, r) => sum + r.assets.reduce((n, a) => n + a.download_count, 0),
          0,
        );
        setStats({ version: latest.tag_name.replace(/^v/, ''), date: latest.published_at, downloads });
      })
      // Rate limits and offline visitors just fall back to the build-time version.
      .catch(() => {});
    return () => ctrl.abort();
  }, []);

  return stats;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' });
}

function RemoteIllustration() {
  return (
    <svg viewBox="0 0 520 250" className="h-auto w-full" role="img" aria-label="A phone sending a link over Wi-Fi to a computer, which saves the file.">
      {/* Phone */}
      <rect x="28" y="14" width="124" height="224" rx="22" fill="#0c1238" />
      <rect x="38" y="30" width="104" height="192" rx="12" fill="#f5f7ff" />
      <rect x="48" y="46" width="84" height="18" rx="6" fill="#fff" stroke="#0c1238" strokeWidth="2" />
      <rect x="54" y="53" width="44" height="4" rx="2" fill="#3b4270" opacity="0.5" />
      <rect x="48" y="76" width="84" height="46" rx="8" fill="#dfe4ff" />
      <circle cx="90" cy="99" r="12" fill="#2342f2" />
      <path d="M86 93 L96 99 L86 105 Z" fill="#fff" />
      <rect x="48" y="134" width="84" height="26" rx="8" fill="#ff5fa8" stroke="#0c1238" strokeWidth="2" />
      <text x="90" y="152" textAnchor="middle" fontFamily="Schibsted Grotesk, sans-serif" fontWeight="800" fontSize="12" fill="#0c1238">Grab</text>
      <rect x="48" y="174" width="84" height="8" rx="4" fill="#dfe4ff" />
      <rect x="48" y="174" width="58" height="8" rx="4" fill="#2342f2" />

      {/* The link travelling over Wi-Fi */}
      <path d="M160 118 C 215 40, 275 40, 326 96" fill="none" stroke="#ffd447" strokeWidth="5" strokeLinecap="round" strokeDasharray="1 13" />
      <g transform="translate(243 52)" fill="none" stroke="#ffd447" strokeWidth="4" strokeLinecap="round">
        <path d="M-16 -2 A22 22 0 0 1 16 -2" />
        <path d="M-9 5 A12 12 0 0 1 9 5" />
        <circle cx="0" cy="11" r="1.5" fill="#ffd447" />
      </g>

      {/* Computer */}
      <rect x="318" y="40" width="182" height="126" rx="12" fill="#0c1238" />
      <rect x="328" y="50" width="162" height="106" rx="6" fill="#0f1d7a" />
      <path d="M342 70 h22 l6 6 h32 v34 h-60 z" fill="#ffd447" />
      {[0, 1, 2].map((i) => (
        <g key={i} transform={`translate(412 ${68 + i * 24})`}>
          <rect width="64" height="16" rx="4" fill="#2342f2" />
          <rect x="6" y="6" width={36 - i * 8} height="4" rx="2" fill="#f5f7ff" />
        </g>
      ))}
      <rect x="342" y="126" width="60" height="16" rx="4" fill="#ff5fa8" />
      <path d="M300 166 H518 L506 186 H312 Z" fill="#0c1238" />
    </svg>
  );
}

export default function App() {
  const [donateOpen, setDonateOpen] = useState(false);
  const [copied, setCopied] = useState<'link' | 'msg' | null>(null);
  const stats = useReleaseStats();
  const os = detectOs();
  const primary = PLATFORMS.find((p) => p.key === os) ?? PLATFORMS[0];

  const pageUrl = typeof window !== 'undefined' ? window.location.href.split('#')[0] : '';

  const copy = async (kind: 'link' | 'msg') => {
    try {
      await navigator.clipboard.writeText(kind === 'link' ? pageUrl : `${SHARE_TEXT} ${pageUrl}`);
      setCopied(kind);
      setTimeout(() => setCopied(null), 2000);
    } catch {
      setCopied(null);
    }
  };

  return (
    <div className="min-h-screen overflow-x-hidden">
      <DonationModal isOpen={donateOpen} onClose={() => setDonateOpen(false)} />

      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-prize focus:px-4 focus:py-2 focus:text-ink">
        Skip to content
      </a>

      <header className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-5 sm:px-8">
        <a href="#top" className="flex items-center gap-3 no-underline">
          <Logo size={40} className="rounded-xl" />
          <span className="display text-2xl">MediaGrab</span>
        </a>
        <nav aria-label="Main" className="flex items-center gap-1 text-[15px] font-semibold sm:gap-2">
          <a href="#remote" className="hidden rounded-lg px-3 py-2 no-underline hover:bg-white/10 md:block">Phone remote</a>
          <a href="#download" className="hidden rounded-lg px-3 py-2 no-underline hover:bg-white/10 sm:block">Download</a>
          <a href="#new" className="hidden rounded-lg px-3 py-2 no-underline hover:bg-white/10 md:block">What’s new</a>
          <a href={REPO} aria-label="MediaGrab on GitHub" className="rounded-lg p-2 hover:bg-white/10">
            <FaGithub size={22} />
          </a>
        </nav>
      </header>

      <main id="main">
        {/* Hero */}
        <section id="top" className="mx-auto grid max-w-6xl items-start gap-12 px-5 pb-40 pt-8 sm:px-8 lg:grid-cols-[1fr_460px] lg:gap-16 lg:pt-16">
          <div className="max-w-xl lg:pt-8">
            <h1 className="display text-[clamp(3.2rem,8vw,5.6rem)]">
              Grab the video. Keep the file.
            </h1>
            <p className="mt-6 max-w-[34rem] text-lg text-white/85 sm:text-xl">
              MediaGrab saves videos and audio from YouTube, TikTok, Instagram and more, straight into a folder on
              your computer. It’s free, there’s no account, and your phone can drive it.
            </p>

            <div className="mt-9 flex flex-wrap items-center gap-4">
              <a href={primary.href} className="arcade-btn bg-prize px-7 py-4 text-lg text-ink">
                <Download size={22} strokeWidth={2.5} />
                Download for {primary.name}
              </a>
              <a href="#download" className="font-semibold underline decoration-2 underline-offset-4 hover:text-prize">
                Other systems
              </a>
            </div>

            <div className="mt-8 text-[15px] text-white/75">
              <p>
                Version {stats?.version ?? APP_VERSION}
                {stats && <>, released {formatDate(stats.date)}</>}
              </p>
              {stats && stats.downloads > 0 && (
                <p>{stats.downloads.toLocaleString()} downloads so far</p>
              )}
            </div>
          </div>

          <div className="flex justify-center lg:justify-end">
            <ClawMachine />
          </div>
        </section>

        {/* Phone remote */}
        <section id="remote" className="bg-glass text-ink">
          <div className="mx-auto grid max-w-6xl items-center gap-12 px-5 py-24 sm:px-8 lg:grid-cols-2">
            <div>
              <h2 className="display text-[clamp(2.4rem,5vw,3.6rem)] text-cobalt">
                Your phone is the joystick.
              </h2>
              <p className="mt-5 max-w-lg text-lg text-ink-soft">
                Found a video on your phone? Send it to your computer. The Android app talks to MediaGrab Server over
                your Wi-Fi, and the file lands on the machine with the big disk.
              </p>

              <ol className="mt-10 space-y-6">
                {[
                  {
                    title: 'Run MediaGrab Server on your computer',
                    body: (
                      <>
                        Get it for{' '}
                        {SERVERS.map((s, i) => (
                          <span key={s.name}>
                            <a href={s.href} className="font-semibold text-cobalt underline underline-offset-2">{s.name}</a>
                            {i < SERVERS.length - 2 ? ', ' : i === SERVERS.length - 2 ? ' or ' : '.'}
                          </span>
                        ))}
                      </>
                    ),
                  },
                  {
                    title: 'Open the Android app on the same Wi-Fi',
                    body: <>It finds the server by itself. If your network hides it, type the computer’s address instead.</>,
                  },
                  {
                    title: 'Paste a link on your phone',
                    body: <>The download runs on the computer and saves to Downloads/MediaGrab, with progress on your phone.</>,
                  },
                ].map((step, i) => (
                  <li key={step.title} className="flex gap-4">
                    <span className="display flex size-11 shrink-0 items-center justify-center rounded-full border-2 border-ink bg-prize text-xl">
                      {i + 1}
                    </span>
                    <div>
                      <h3 className="text-lg font-bold">{step.title}</h3>
                      <p className="mt-1 text-ink-soft">{step.body}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </div>

            <div className="rounded-[28px] border-2 border-ink bg-cobalt p-6 shadow-[0_10px_0_var(--color-ink)] sm:p-8">
              <RemoteIllustration />
            </div>
          </div>
        </section>

        {/* What it handles */}
        <section className="mx-auto max-w-6xl px-5 py-24 sm:px-8">
          <h2 className="display max-w-2xl text-[clamp(2.4rem,5vw,3.6rem)]">What goes in the machine</h2>
          <dl className="mt-12 grid gap-x-12 gap-y-10 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(({ icon: Icon, title, body }) => (
              <div key={title} className="border-t-2 border-white/25 pt-5">
                <dt className="flex items-center gap-3 text-lg font-bold">
                  <Icon size={22} className="shrink-0 text-prize" aria-hidden="true" />
                  {title}
                </dt>
                <dd className="mt-2 text-white/80">{body}</dd>
              </div>
            ))}
          </dl>
        </section>

        {/* Downloads */}
        <section id="download" className="bg-cobalt-deep">
          <div className="mx-auto max-w-6xl px-5 py-24 sm:px-8">
            <h2 className="display text-[clamp(2.4rem,5vw,3.6rem)]">Pick your machine</h2>
            <p className="mt-4 max-w-xl text-lg text-white/80">
              Version {APP_VERSION}. Every file comes from the{' '}
              <a href={ALL_RELEASES} className="font-semibold underline underline-offset-4 hover:text-prize">GitHub release</a>,
              built by the project’s own release workflow.
            </p>

            <ul className="mt-12 overflow-hidden rounded-[24px] border-2 border-ink bg-glass text-ink shadow-[0_10px_0_var(--color-ink)]">
              {PLATFORMS.map((p) => {
                const mine = p.key === os;
                const Icon = p.icon;
                return (
                  <li
                    key={p.key}
                    className={`grid gap-4 border-b-2 border-ink/10 px-5 py-6 last:border-b-0 sm:px-7 md:grid-cols-[auto_1fr_auto] md:items-center md:gap-8 ${
                      mine ? 'bg-prize' : ''
                    }`}
                  >
                    <div className="flex items-center gap-4 md:w-60">
                      <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-ink text-white">
                        <Icon size={24} aria-hidden="true" />
                      </span>
                      <div>
                        <h3 className="text-xl font-extrabold">{p.name}</h3>
                        {mine && <p className="text-sm font-semibold">Matches this device</p>}
                      </div>
                    </div>

                    <div className="min-w-0">
                      <p className="text-ink-soft">{p.requirement}</p>
                      <p className="mt-1 break-all text-sm font-semibold">
                        {p.file} <span className="font-normal text-ink-soft">({p.size})</span>
                      </p>
                    </div>

                    <div className="flex flex-col items-start gap-1 md:items-end">
                      <a
                        href={p.href}
                        className={`arcade-btn px-5 py-3 ${mine ? 'bg-ink text-white' : 'bg-white text-ink'}`}
                      >
                        <Download size={18} strokeWidth={2.5} />
                        Download
                      </a>
                      {p.extra && (
                        <a href={p.extra.href} className="text-sm font-semibold underline underline-offset-2">
                          {p.extra.label}
                        </a>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        </section>

        {/* What's new */}
        <section id="new" className="mx-auto grid max-w-6xl gap-12 px-5 py-24 sm:px-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
          <div>
            <h2 className="text-lg font-semibold text-white/80">What’s new</h2>
            <p className="display mt-2 text-[clamp(4rem,11vw,7rem)] text-prize">{APP_VERSION}</p>
            <p className="mt-4 max-w-sm text-lg text-white/85">
              A repair release. The download engine from 1.0.0 was fixed end to end and is now covered by tests.
            </p>
            <a href={CHANGELOG} className="arcade-btn mt-8 bg-white px-5 py-3 text-ink">
              Read the full changelog
            </a>
          </div>

          <ul className="divide-y-2 divide-white/20 border-y-2 border-white/20">
            {HIGHLIGHTS.map((h) => (
              <li key={h.title} className="py-7">
                <h3 className="text-xl font-bold">{h.title}</h3>
                <p className="mt-2 max-w-xl text-white/80">{h.body}</p>
              </li>
            ))}
          </ul>
        </section>

        {/* Support */}
        <section className="bg-glass text-ink">
          <div className="mx-auto grid max-w-6xl gap-12 px-5 py-24 sm:px-8 lg:grid-cols-2">
            <div>
              <h2 className="display text-[clamp(2.2rem,4.5vw,3.2rem)] text-cobalt">Know someone who’d use it?</h2>
              <p className="mt-4 max-w-md text-lg text-ink-soft">Send them the link. That’s the best help there is.</p>

              <div className="mt-8 flex flex-wrap gap-2">
                {SHARE.map(({ icon: Icon, name, url }) => (
                  <a
                    key={name}
                    href={url(encodeURIComponent(pageUrl), encodeURIComponent(SHARE_TEXT))}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 rounded-full border-2 border-ink bg-white px-4 py-2 text-sm font-semibold no-underline hover:bg-prize"
                  >
                    <Icon size={15} aria-hidden="true" />
                    {name}
                  </a>
                ))}
              </div>

              <div className="mt-6 flex flex-wrap gap-3">
                <button type="button" onClick={() => copy('link')} className="arcade-btn bg-white px-4 py-2.5 text-ink">
                  {copied === 'link' ? <Check size={18} /> : <Copy size={18} />}
                  {copied === 'link' ? 'Link copied' : 'Copy link'}
                </button>
                <button type="button" onClick={() => copy('msg')} className="arcade-btn bg-white px-4 py-2.5 text-ink">
                  {copied === 'msg' ? <Check size={18} /> : <Share2 size={18} />}
                  {copied === 'msg' ? 'Message copied' : 'Copy a message'}
                </button>
              </div>
            </div>

            <div className="flex flex-col justify-between rounded-[28px] border-2 border-ink bg-capsule p-8 shadow-[0_10px_0_var(--color-ink)] sm:p-10">
              <div>
                <Heart size={36} strokeWidth={2.5} aria-hidden="true" />
                <h2 className="display mt-5 text-[clamp(2rem,4vw,2.8rem)]">Keep it free</h2>
                <p className="mt-3 max-w-md text-lg">
                  MediaGrab has no ads and never will. If it saved you some time, you can chip in toward keeping it going.
                </p>
              </div>
              <button type="button" onClick={() => setDonateOpen(true)} className="arcade-btn mt-8 self-start bg-white px-6 py-3 text-lg text-ink">
                Support MediaGrab
              </button>
            </div>
          </div>
        </section>
      </main>

      <footer className="mx-auto flex max-w-6xl flex-col gap-6 px-5 py-12 text-[15px] text-white/75 sm:flex-row sm:items-center sm:justify-between sm:px-8">
        <div className="flex items-center gap-3">
          <Logo size={28} className="rounded-lg" />
          <p>MediaGrab is open source under the MIT License, built on yt-dlp and FFmpeg.</p>
        </div>
        <ul className="flex flex-wrap gap-5 font-semibold">
          <li><a href={REPO} className="hover:text-prize">Source code</a></li>
          <li><a href={ALL_RELEASES} className="hover:text-prize">All releases</a></li>
          <li><a href={`${REPO}/issues`} className="hover:text-prize">Report a problem</a></li>
        </ul>
      </footer>
    </div>
  );
}
