# Resume brief — read this first in a new session

**Repo:** https://github.com/mithukosuri-star/pratmusic  ·  clone: `git clone https://github.com/mithukosuri-star/pratmusic.git`
(_audio not in repo — regenerate with `python3 tools/build_library.py`, needs `pip install pillow`)_

## What this project is
An offline-first installable music PWA (vanilla JS, no build step) with:
glass/aurora UI that re-themes per track, WebAudio visualizer (3 modes), two-deck crossfade,
queue/shuffle/repeat/favorites/sleep-timer, Media Session (OS media keys), IndexedDB imports
("Your music"), and a service worker that caches app + all audio **including HTTP Range**, so
seeking works fully offline. Headless-Chromium tested: playback, offline reload, offline seek,
imports, favorites persistence — 0 console errors.

## Current state (done & verified)
- Full player app in this folder; run with `python3 server.py 8000` (binds 0.0.0.0, Range-capable).
- Bundled catalogue: 13 open-licensed (CC/PD) tracks, 49 min, real cover art, attribution in-app
  + `CREDITS.md`. Audio kept unmodified (several licences are NoDerivatives).
- `tools/build_library.py` re-downloads the whole catalogue (media + covers + library.json)
  from the Internet Archive in ~15 s. Verified reproducible. **The handoff zip omits `media/`
  (70 MB) on purpose — regenerate it with that script.**
- Branding renamed to **PratMusic** (UI, manifest, sw cache `pratmusic-v1`, LS keys `pratmusic.*`,
  IndexedDB `pratmusic-db`, folder `pratmusic/`).

## Pending work (the user's last request, interrupted)
1. ~~Rename to PratMusic~~ DONE.
2. **Add "similar English songs"** in the vibe of Lana Del Rey / The Neighbourhood / Dua Lipa /
   Rihanna / Lady Gaga. ⚠️ Their actual masters are major-label copyrighted — do NOT bundle or
   rip them. Deliverable = openly-licensed vibe matches (dream pop / dark indie pop / synth-pop /
   dance-disco pop with vocals) added via the same pipeline (`tools/build_library.py` PICKS list),
   plus a first-class "bring your own files" panel naming those artists so files the user owns
   drop in and play offline.
   Searching archive.org: netlabels skew instrumental/disco; broad `mediatype:(audio) AND
   licenseurl:(*creativecommons*) AND subject:(dream pop|indie pop|synthpop)` was the next step.
3. Re-run the puppeteer smoke test after changes (see below), bump `sw.js` VERSION on every
   asset change.

## Test recipe (worked before)
```bash
mkdir -p /tmp/smoke && cd /tmp/smoke && npm i puppeteer
sudo -n apt-get install -y -qq libnspr4 libnss3 libatk1.0-0t64 libatk-bridge2.0-0t64 libcups2t64 \
  libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 \
  libasound2t64 libatspi2.0-0t64        # chrome shared libs, only if launch fails
node -e "<launch with --no-sandbox --autoplay-policy=no-user-gesture-required, click .card .cov, assert #player.playing>"
```
Offline test: `page.setOfflineMode(true)` then reload `#home` (NOT a hash view without cards).

## Gotchas learned the hard way
- archive.org `advancedsearch.php` needs `doseq=True` for repeated `fl[]` params; requesting
  `licenseurl` in `fl` breaks results — fetch licences from `/metadata/<id>` instead.
- Keep audio files byte-identical (ND licences); never re-encode/trim.
- `SimpleHTTPRequestHandler` has no Range support → keep `server.py`.
- SW must slice cached blobs for `Range:` or offline seeking breaks (already implemented).
