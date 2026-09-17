/**
 * The hero: a playable claw machine.
 *
 * Paste a link, press Grab, and the claw fetches the capsule for that
 * platform and drops it down the chute, which prints a ticket for the file.
 * It is a demo of the idea only; nothing is downloaded.
 */
import { useRef, useState } from 'react';
import { AnimatePresence, motion, useAnimate, useReducedMotion } from 'framer-motion';

interface Prize {
  code: string;
  name: string;
  hosts: string[];
  x: number;
  y: number;
  color: string;
}

const PINK = '#ff5fa8';
const YELLOW = '#ffd447';
const VIOLET = '#8b5cf6';
const CYAN = '#3cd3f5';
const ORANGE = '#ff8a3d';

// Two staggered rows on the machine floor, radius 21.
const PRIZES: Prize[] = [
  { code: 'YT', name: 'YouTube', hosts: ['youtube.com', 'youtu.be'], x: 150, y: 288, color: PINK },
  { code: 'TT', name: 'TikTok', hosts: ['tiktok.com'], x: 196, y: 288, color: CYAN },
  { code: 'IG', name: 'Instagram', hosts: ['instagram.com', 'instagr.am'], x: 242, y: 288, color: ORANGE },
  { code: 'X', name: 'X', hosts: ['twitter.com', 'x.com'], x: 288, y: 288, color: YELLOW },
  { code: 'VM', name: 'Vimeo', hosts: ['vimeo.com'], x: 334, y: 288, color: VIOLET },
  { code: 'RD', name: 'Reddit', hosts: ['reddit.com', 'redd.it'], x: 380, y: 288, color: ORANGE },
  { code: 'TW', name: 'Twitch', hosts: ['twitch.tv'], x: 173, y: 252, color: VIOLET },
  { code: 'FB', name: 'Facebook', hosts: ['facebook.com', 'fb.watch'], x: 219, y: 252, color: CYAN },
  { code: 'DM', name: 'Dailymotion', hosts: ['dailymotion.com', 'dai.ly'], x: 265, y: 252, color: YELLOW },
  { code: 'www', name: 'Any link', hosts: [], x: 311, y: 252, color: PINK },
  { code: 'www', name: 'Any link', hosts: [], x: 357, y: 252, color: CYAN },
];

const SAMPLES = [
  'https://www.youtube.com/watch?v=jNQXAC9IVRw',
  'https://vimeo.com/76979871',
  'https://www.tiktok.com/@nasa/video/7243356917353000234',
  'https://x.com/NASA/status/1631776452342583296',
];

const HOME = { x: 68, y: 44 };
const GRIP = 34; // distance from the claw hub down to a held capsule's centre

type Format = 'mp4' | 'mp3';

interface Ticket {
  file: string;
  platform: string;
}

function pickPrize(url: URL, taken: number | null): number {
  const host = url.hostname.toLowerCase();
  const match = PRIZES.findIndex((p) => p.hosts.some((h) => host === h || host.endsWith(`.${h}`)));
  if (match !== -1) return match;
  const generic = PRIZES.map((p, i) => ({ p, i })).filter(({ p, i }) => p.code === 'www' && i !== taken);
  return generic[Math.floor(Math.random() * generic.length)].i;
}

function fileNameFor(url: URL, format: Format): string {
  const tail =
    url.searchParams.get('v') ||
    url.pathname.split('/').filter(Boolean).pop() ||
    url.hostname.replace(/^www\./, '');
  const slug = decodeURIComponent(tail)
    .replace(/\.[a-z0-9]{2,4}$/i, '')
    .replace(/[^a-z0-9]+/gi, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 28);
  return `${slug || 'video'}.${format}`;
}

function Capsule({ prize, hidden }: { prize: Prize; hidden?: boolean }) {
  return (
    <g transform={`translate(${prize.x} ${prize.y})`} opacity={hidden ? 0 : 1} aria-hidden="true">
      <CapsuleBody prize={prize} />
    </g>
  );
}

function CapsuleBody({ prize }: { prize: Prize }) {
  return (
    <>
      <circle r="21" fill="#fff" />
      <path d="M-21 0 A21 21 0 0 1 21 0 Z" fill={prize.color} />
      <line x1="-21" y1="0" x2="21" y2="0" stroke="#0c1238" strokeOpacity="0.25" strokeWidth="1.5" />
      <ellipse cx="-8" cy="-11" rx="6" ry="3.5" fill="#fff" opacity="0.55" />
      <text
        y="13"
        textAnchor="middle"
        fontFamily="Schibsted Grotesk, system-ui, sans-serif"
        fontWeight="800"
        fontSize={prize.code.length > 2 ? 8.5 : 10}
        fill="#0c1238"
      >
        {prize.code}
      </text>
    </>
  );
}

export default function ClawMachine() {
  const reduce = useReducedMotion();
  const [scope, animate] = useAnimate();
  const clawRef = useRef<SVGGElement>(null);
  const leftRef = useRef<SVGPathElement>(null);
  const rightRef = useRef<SVGPathElement>(null);
  const heldRef = useRef<SVGGElement>(null);

  const [link, setLink] = useState('');
  const [format, setFormat] = useState<Format>('mp4');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [grabbed, setGrabbed] = useState<number | null>(null);
  const [held, setHeld] = useState<number | null>(null);
  const [ticket, setTicket] = useState<Ticket | null>(null);

  const t = (seconds: number) => (reduce ? 0 : seconds);

  async function grab() {
    if (busy) return;

    let raw = link.trim();
    if (!raw) {
      raw = SAMPLES[Math.floor(Math.random() * SAMPLES.length)];
      setLink(raw);
    }

    let url: URL;
    try {
      url = new URL(raw);
      if (!/^https?:$/.test(url.protocol)) throw new Error('not http');
    } catch {
      setError("That isn't a web link. Paste one that starts with https://");
      return;
    }

    setError('');
    setBusy(true);
    setTicket(null);

    const index = pickPrize(url, grabbed);
    const prize = PRIZES[index];
    const claw = clawRef.current!;
    const left = leftRef.current!;
    const right = rightRef.current!;
    const ease = 'easeInOut' as const;

    // A capsule taken last round respawns before the next grab.
    setGrabbed(null);

    await animate(claw, { x: prize.x }, { duration: t(0.8), ease });
    await Promise.all([
      animate(left, { rotate: 12 }, { duration: t(0.15) }),
      animate(right, { rotate: -12 }, { duration: t(0.15) }),
    ]);
    await animate(claw, { y: prize.y - GRIP }, { duration: t(0.7), ease: 'easeIn' });
    await Promise.all([
      animate(left, { rotate: -16 }, { duration: t(0.2) }),
      animate(right, { rotate: 16 }, { duration: t(0.2) }),
    ]);

    setGrabbed(index);
    setHeld(index);

    await animate(claw, { y: HOME.y }, { duration: t(0.7), ease: 'easeOut' });
    await animate(claw, { x: HOME.x }, { duration: t(0.9), ease });
    await Promise.all([
      animate(left, { rotate: 8 }, { duration: t(0.15) }),
      animate(right, { rotate: -8 }, { duration: t(0.15) }),
    ]);

    if (heldRef.current) {
      await animate(heldRef.current, { y: 170, opacity: [1, 1, 0] }, { duration: t(0.55), ease: 'easeIn' });
      setHeld(null);
      await animate(heldRef.current, { y: 0, opacity: 1 }, { duration: 0 });
    }

    setTicket({ file: fileNameFor(url, format), platform: prize.name });
    setBusy(false);
  }

  const heldPrize = held !== null ? PRIZES[held] : null;

  return (
    <div className="w-full max-w-[460px]">
      {/* Cabinet */}
      <div
        ref={scope}
        className="relative rounded-[28px] border-2 border-ink bg-cobalt-deep p-3 shadow-[0_10px_0_var(--color-ink)]"
      >
        <div className="flex items-center justify-between px-2 pb-2">
          <span className="display text-lg text-prize">Grab-o-matic</span>
          <span className="flex gap-1.5" aria-hidden="true">
            {[PINK, YELLOW, CYAN].map((c) => (
              <span key={c} className="size-2.5 rounded-full border border-ink" style={{ background: c }} />
            ))}
          </span>
        </div>

        <svg
          viewBox="0 0 420 332"
          className="block w-full rounded-[18px]"
          role="img"
          aria-label={
            ticket
              ? `The claw dropped a ${ticket.platform} capsule into the chute.`
              : 'A claw machine full of capsules labelled with video sites.'
          }
        >
          <defs>
            <clipPath id="mg-glass">
              <rect x="0" y="0" width="420" height="332" rx="16" />
            </clipPath>
            <linearGradient id="mg-shine" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="#fff" stopOpacity="0.14" />
              <stop offset="0.45" stopColor="#fff" stopOpacity="0" />
            </linearGradient>
          </defs>

          <g clipPath="url(#mg-glass)">
            <rect width="420" height="332" fill="#0f1d7a" />

            {/* Rail */}
            <rect x="0" y="0" width="420" height="26" fill="#0c1238" />
            <rect x="12" y="11" width="396" height="4" rx="2" fill="#2342f2" />

            {/* Chute: this is where your file lands */}
            <rect x="24" y="206" width="88" height="140" rx="6" fill="#081256" />
            <text
              x="68"
              y="316"
              textAnchor="middle"
              fontFamily="Schibsted Grotesk, system-ui, sans-serif"
              fontWeight="700"
              fontSize="11"
              fill="#8fa2ff"
            >
              your folder
            </text>

            {/* Floor and prizes */}
            <rect x="120" y="310" width="300" height="30" fill="#0a1560" />
            {PRIZES.map((p, i) => (
              <Capsule key={`${p.code}-${i}`} prize={p} hidden={grabbed === i} />
            ))}

            {/* Claw */}
            <motion.g ref={clawRef} initial={{ x: HOME.x, y: HOME.y }}>
              <line x1="0" y1="-400" x2="0" y2="-6" stroke="#c9d1ff" strokeWidth="2" />
              <rect x="-15" y="-10" width="30" height="14" rx="5" fill="#e8ecff" stroke="#0c1238" strokeWidth="2" />

              <g ref={heldRef}>
                {heldPrize && (
                  <g transform={`translate(0 ${GRIP})`}>
                    <CapsuleBody prize={heldPrize} />
                  </g>
                )}
              </g>

              <motion.path
                ref={leftRef}
                d="M -7 4 L -20 22 Q -25 36 -11 45"
                fill="none"
                stroke="#e8ecff"
                strokeWidth="5"
                strokeLinecap="round"
                initial={{ rotate: 8 }}
                style={{ originX: 1, originY: 0 }}
              />
              <motion.path
                ref={rightRef}
                d="M 7 4 L 20 22 Q 25 36 11 45"
                fill="none"
                stroke="#e8ecff"
                strokeWidth="5"
                strokeLinecap="round"
                initial={{ rotate: -8 }}
                style={{ originX: 0, originY: 0 }}
              />
            </motion.g>

            {/* Chute lip drawn over the claw so a dropped capsule sinks into it */}
            <rect x="18" y="200" width="100" height="12" rx="6" fill="#2342f2" stroke="#0c1238" strokeWidth="2" />

            <rect width="420" height="332" fill="url(#mg-shine)" pointerEvents="none" />
          </g>
        </svg>

        {/* Control panel */}
        <form
          className="mt-3 rounded-[18px] border-2 border-ink bg-glass p-3 text-ink"
          onSubmit={(e) => {
            e.preventDefault();
            void grab();
          }}
        >
          <label htmlFor="claw-link" className="mb-1.5 block text-sm font-semibold text-ink-soft">
            Paste a video link, or leave it empty for a random one
          </label>
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              id="claw-link"
              type="url"
              inputMode="url"
              autoComplete="off"
              spellCheck={false}
              placeholder="https://youtu.be/…"
              value={link}
              onChange={(e) => {
                setLink(e.target.value);
                if (error) setError('');
              }}
              aria-invalid={Boolean(error)}
              aria-describedby={error ? 'claw-error' : undefined}
              className="min-w-0 flex-1 rounded-xl border-2 border-ink bg-white px-3 py-2.5 text-base text-ink placeholder:text-ink-soft/60 focus:outline-none focus-visible:border-cobalt"
            />
            <div className="flex gap-2">
              <div role="radiogroup" aria-label="File type" className="flex rounded-xl border-2 border-ink bg-white p-0.5">
                {(['mp4', 'mp3'] as const).map((f) => (
                  <button
                    key={f}
                    type="button"
                    role="radio"
                    aria-checked={format === f}
                    onClick={() => setFormat(f)}
                    className={`rounded-[9px] px-3 text-sm font-bold uppercase transition-colors ${
                      format === f ? 'bg-ink text-white' : 'text-ink-soft hover:text-ink'
                    }`}
                  >
                    {f}
                  </button>
                ))}
              </div>
              <button
                type="submit"
                disabled={busy}
                className="arcade-btn flex-1 bg-capsule px-6 py-2.5 text-lg text-ink disabled:cursor-wait disabled:opacity-70 sm:flex-none"
              >
                {busy ? 'Grabbing…' : 'Grab'}
              </button>
            </div>
          </div>
          {error && (
            <p id="claw-error" role="alert" className="mt-2 text-sm font-semibold text-[#c21a5e]">
              {error}
            </p>
          )}
        </form>
      </div>

      {/* Ticket printer */}
      <div className="relative mx-6 h-0" aria-live="polite">
        <AnimatePresence>
          {ticket && (
            <motion.div
              key={ticket.file}
              initial={{ clipPath: reduce ? 'inset(0 0 0 0)' : 'inset(0 0 100% 0)' }}
              animate={{ clipPath: 'inset(0 0 0 0)' }}
              exit={{ opacity: 0 }}
              transition={{ duration: reduce ? 0 : 0.6, ease: 'easeOut' }}
              className="absolute inset-x-0 top-0 z-10 rounded-b-xl border-2 border-t-0 border-ink bg-prize px-4 pb-4 pt-3 text-ink shadow-[0_6px_0_var(--color-ink)]"
            >
              <p className="text-sm font-semibold text-ink-soft">Won from {ticket.platform}</p>
              <p className="break-all text-lg font-extrabold leading-snug">{ticket.file}</p>
              <p className="mt-1 text-sm">
                This one was pretend. The app saves the real file to Downloads/MediaGrab.
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
