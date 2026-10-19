/* Full-length streams from the curated Internet Archive open-license catalog.
   Metadata is resolved in the browser, so static hosting needs no API keys. */
const OnlineMusic = (() => {
  const norm = value => String(value || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  const text = value => Array.isArray(value) ? value[0] : value;
  async function getJSON(url) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);
    try {
      const res = await fetch(url, { signal: controller.signal });
      if (!res.ok) throw new Error('Music provider unavailable. Please retry.');
      return await res.json();
    } finally { clearTimeout(timer); }
  }
  function seconds(value) {
    return String(value || '0').split(':').reduce((total, part) => total * 60 + (Number(part) || 0), 0);
  }
  async function search(term) {
    const catalog = await getJSON('free-catalog.json');
    const query = String(term || '').trim().toLowerCase();
    const matches = catalog.filter(t => !query || [t.title, t.artist, t.genre, t.mood, t.album].join(' ').toLowerCase().includes(query));
    const metadata = new Map();
    const results = new Array(matches.length);
    let cursor = 0, failures = 0;
    async function worker() {
      while (cursor < matches.length) {
        const index = cursor++, track = matches[index];
        try {
          if (!metadata.has(track.sourceId)) metadata.set(track.sourceId, getJSON(`https://archive.org/metadata/${encodeURIComponent(track.sourceId)}`));
          const item = await metadata.get(track.sourceId);
          const license = text(item.metadata?.licenseurl) || '';
          // Do not infer permission from a public download URL alone.
          if (!/^https?:\/\/(www\.)?creativecommons.org\/(licenses|publicdomain)\//i.test(license)) continue;
          const wanted = norm(track.matchTitle);
          const files = (item.files || []).filter(f => /\.mp3$/i.test(f.name || '') &&
            (norm(f.title || f.name).includes(wanted) || norm(f.title || f.name).includes(wanted.slice(0,18))));
          files.sort((a,b) => (Number(a.size) || Infinity) - (Number(b.size) || Infinity));
          const file = files[0];
          if (!file) continue;
          results[index] = { ...track, kind: 'online',
            title: text(file.title) || track.title,
            artist: text(file.artist) || text(item.metadata.creator) || track.artist,
            album: text(item.metadata.title) || track.album,
            duration: seconds(file.length),
            file: `https://archive.org/download/${encodeURIComponent(track.sourceId)}/${file.name.split('/').map(encodeURIComponent).join('/')}`,
            license, licenseName: track.licenseName + ' · full track',
            source: `https://archive.org/details/${encodeURIComponent(track.sourceId)}`
          };
        } catch { failures++; }
      }
    }
    await Promise.all(Array.from({length:Math.min(3,matches.length)}, worker));
    const tracks = results.filter(Boolean);
    if (failures && !tracks.length) throw new Error('Cannot reach the free music provider. Check your connection and retry.');
    return tracks;
  }
  return { search };
})();
