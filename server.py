#!/usr/bin/env python3
"""PratMusic dev/preview server — static files + HTTP Range support (audio seeking)."""
import os, re, sys, socket
if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000

class Handler(SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        '.webmanifest': 'application/manifest+json',
        '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css',
        '.json': 'application/json', '.mp3': 'audio/mpeg', '.wav': 'audio/wav',
        '.ogg': 'audio/ogg', '.flac': 'audio/flac', '.opus': 'audio/opus',
        '.m4a': 'audio/mp4', '.svg': 'image/svg+xml',
        '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2',
    }

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(404, 'File not found')
            return None
        try:
            size = os.fstat(f.fileno()).st_size
            ctype = self.guess_type(path)
            rng = self.headers.get('Range')
            m = re.match(r'bytes=(\d*)-(\d*)', rng or '')
            if rng and m and (m.group(1) or m.group(2)):
                s, e = m.group(1), m.group(2)
                if s == '':
                    start, end = size - int(e), size - 1
                else:
                    start, end = int(s), (int(e) if e else size - 1)
                start, end = max(0, start), min(end, size - 1)
                if start > end:
                    # RFC 9110: a 416 must report the current length of the file.
                    self.send_response(416)
                    self.send_header('Content-Range', f'bytes */{size}')
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    f.close(); return None
                self.send_response(206)
                self.send_header('Content-Type', ctype)
                self.send_header('Accept-Ranges', 'bytes')
                self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
                self.send_header('Content-Length', str(end - start + 1))
                self.send_header('Cache-Control', self._cache_control(path))
                self.end_headers()
                f.seek(start)
                return _Limit(f, end - start + 1)
            self.send_response(200)
            self.send_header('Content-Type', ctype)
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Content-Length', str(size))
            self.send_header('Cache-Control', self._cache_control(path))
            self.end_headers()
            return f
        except Exception:
            f.close(); raise

    @staticmethod
    def _cache_control(path):
        # App shell / metadata must always revalidate; media is immutable.
        # Same policy for full (200) and partial (206) responses.
        if path.endswith(('.html', '.webmanifest', '.json', '.js', '.css')):
            return 'no-cache'
        return 'public, max-age=31536000, immutable'

    def copyfile(self, source, outputfile):
        # Browsers abort audio transfers constantly (seeking, skipping tracks);
        # that is normal, not an error worth a traceback.
        try:
            super().copyfile(source, outputfile)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            self.close_connection = True

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

class _Limit:
    def __init__(self, f, n): self.f, self.n = f, n
    def read(self, b=-1):
        if self.n <= 0: return b''
        d = self.f.read(min(b, self.n) if b and b > 0 else self.n)
        self.n -= len(d); return d
    def close(self): self.f.close()

class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

if __name__ == '__main__':
    os.chdir(ROOT)
    srv = Server(('0.0.0.0', PORT), Handler)
    print(f'PratMusic serving {ROOT} on 0.0.0.0:{PORT}', flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
