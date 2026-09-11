# Changelog

## 1.1.0

Audit and repair release. Every item below is a defect found in 1.0.0.

### Downloads could not start or report progress

- **Starting any download returned HTTP 500.** `/download/start` and
  `/download/retry` passed the future from `run_in_executor` to
  `asyncio.create_task`, which only accepts coroutines.
- **Progress was stuck at 0% everywhere.** yt-dlp strips the `download:` prefix
  from `--progress-template`, so the marker both parsers matched on never
  appeared in its output. The marker now lives in the template body, and one
  shared parser in `shared/yt_dlp_helper.py` serves the backend and the desktop
  app. Verified end to end against a real yt-dlp run.
- **The default download request was rejected.** The default `output_dir` was an
  absolute path, and the validator accepts only relative subfolders. Requests
  now default to the configured root.
- **Quality choices produced invalid yt-dlp selectors.** The mobile app sent
  labels such as `720p` straight into `-f`. `normalize_quality()` now converts a
  label into a real selector wherever one is used.
- **A single video with a `list=` parameter downloaded the whole playlist.**
  Playlist detection is now an explicit URL check, and non-playlist downloads
  pass `--no-playlist`.

### Data loss and security

- **Cancelling a download deleted unrelated files.** The cleanup matched any
  name containing `.f`, so `song.flac` in the same folder was removed. It now
  matches only yt-dlp temp patterns, and only files written after the download
  started.
- **The "Delete" button on a desktop history card offered to delete the entire
  download folder**, which for non-playlist downloads is the shared root. It now
  targets only that download's file, and "Clear History" no longer touches files
  at all.
- **The progress websocket had no authentication.** Any device on the network
  could stream any task. It now checks the API key and task ownership.
- **Task ownership broke across restarts.** Client fallback ids used `hash()`,
  whose string seed is randomised per process; they now use SHA-256.
- API keys are compared with `secrets.compare_digest`, and the "no API key"
  warning is logged once at startup rather than on every request.

### Reliability

- **Long downloads were evicted from the progress registry after an hour**,
  leaving clients unable to poll them. Only finished tasks are now retired.
- **A completed desktop download crashed on the history card** (`KeyError:
  'title'`), because progress updates replaced the card's data instead of
  merging into it.
- **Cancelling a playlist download on the server did nothing** between items.
  The active child downloader is now published so cancel reaches it.
- **`/download/retry` crashed on direct HTTP downloads**, which had no `_status`
  attribute. Retry now reads task state instead of a private attribute.
- **mDNS failure took the whole server down at startup.** Discovery is now
  best-effort, and it advertises the configured port rather than a hardcoded
  8000.
- Direct HTTP downloads clean up their partial file on cancel or error, honour
  `Content-Disposition` for the filename, and throttle progress updates.
- `/health` reports actual uptime instead of the current epoch time.

### Mobile app

- **Playlist selection did nothing.** The chosen entries were collected and then
  discarded; every playlist download ran as a single-URL download. Selections
  now reach `/download/playlist`, with per-item progress on screen.
- mDNS discovery never matched the server: the service type was passed
  pre-formatted, producing `__mediagrab._tcp.._tcp.`.
- A successful subnet scan did not save the address it found.
- The websocket fallback timer and the 30-minute timeout shared one ref, so the
  first could never be cleared.
- The URL auto-analyze timer kept running after the screen was unmounted, and
  fired before a server was connected.
- Requests now send a stable `X-Client-ID` instead of relying on IP fallback.

### New look

- **New app mark**: a download arrow caught by a pair of brackets, in the brand
  blue-to-violet gradient. It replaces the unrelated stock glyph that shipped as
  the favicon and the plain "M" tile on the site. Rendered from one source
  geometry into every size the project needs: site favicon and logo, Windows
  `.ico`, macOS `.icns`, and the Android icon, adaptive icon and splash, which
  was previously a 67-byte placeholder.
- The built Windows executable had no icon at all, and the desktop window used
  the default Tk icon. Both now carry the app mark.
- **Redesigned download page.** The platform cards were plain slate boxes that
  ignored the site's own glass styling. They are now one data-driven grid with
  per-platform accents, the exact asset filename and size, a highlighted card
  for the visitor's own OS, and a link to the tarball for Linux users who do not
  want the AppImage.
- **Added a "What's new" section** summarising this release, plus a version pill
  in the nav and a release ribbon in the hero, both linking to the changelog.
- Added Open Graph and Twitter card metadata, an SVG favicon, and a theme
  colour, so shared links preview properly.
- Download links pointed at hardcoded v1.0.0 assets, and the Linux link pointed
  at a file the release workflow never produces. Asset URLs are now built from
  the repo `VERSION` at build time and use the real asset names.

### Housekeeping

- Desktop uninstall cleanup looked for config and history in platform app-data
  folders; the app writes them to the home directory. Both are now cleaned.
- The desktop app checks free disk space before starting a download.
- `download_orchestrator.py` imported a backend-only module and called an async
  function without awaiting it; it now uses the desktop's own download engine.
- Repaired mis-encoded characters in three desktop modules.
- Backend dependencies use lower bounds rather than exact pins, which had no
  wheels on current Python versions.
- Added `backend/tests/` (36 tests) and wired them into CI.

## 1.0.0

Initial release.
