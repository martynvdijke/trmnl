#!/usr/bin/env python3
"""Local reverse proxy for serving trmnl/trmnlp behind Nginx Proxy Manager.

The trmnl serve container (Sinatra/Rack) enforces Rack::Protection::HostAuthorization
with a fixed SERVER_NAME of 127.0.0.1. When reached through NPM the request carries
X-Forwarded-For with the public client IP and a Host/X-Forwarded-Host of the public
domain, so Rack treats the client as untrusted and rejects the host mismatch
("Host not permitted").

This proxy listens on :4567 (what NPM forwards to) and forwards to the trmnl serve
container on :4568 with Host forced to 127.0.0.1 and all X-Forwarded-* stripped, so
trmnl sees a trusted loopback client and renders fine. Because the upstream only ever
sees Host: 127.0.0.1, any redirect it emits (e.g. / -> /full) would point at
https://127.0.0.1/... which the browser cannot reach. We therefore rewrite the
response Location header back to the original public host/scheme.

Run order:
  docker run -d --name trmnl-preview -p 4568:4567 \
    --volume "$(pwd)/plugins/<name>:/plugin" trmnl/trmnlp serve --bind 0.0.0.0
  python3 scripts/trmnl-proxy.py
"""
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
import http.client

UPSTREAM_HOST = '127.0.0.1'
UPSTREAM_PORT = 4568


class Proxy(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def _rewrite_location(self, location, orig_host, orig_proto):
        try:
            parsed = urllib.parse.urlparse(location)
            if not parsed.netloc:
                # relative path -> absolutize against the original host
                return f"{orig_proto}://{orig_host}{location}"
            new = parsed._replace(scheme=orig_proto, netloc=orig_host)
            return urllib.parse.urlunparse(new)
        except Exception:
            return location.replace('127.0.0.1', orig_host)

    def _proxy(self):
        # Capture the real host/scheme the browser used (NPM sends X-Forwarded-Proto).
        orig_host = self.headers.get('Host', '127.0.0.1')
        orig_proto = self.headers.get('X-Forwarded-Proto')
        if not orig_proto:
            host_only = orig_host.split(':')[0]
            orig_proto = 'http' if host_only in ('localhost', '127.0.0.1') else 'https'

        headers = {}
        for k, v in self.headers.items():
            if k.lower().startswith('x-forwarded'):
                continue
            headers[k] = v
        # SERVER_NAME is fixed to 127.0.0.1 in the trmnl container, so the host
        # check only passes when we present Host: 127.0.0.1 with no public XFF.
        headers['Host'] = '127.0.0.1'

        body = None
        if self.command in ('POST', 'PUT', 'PATCH'):
            length = int(self.headers.get('Content-Length', 0) or 0)
            body = self.rfile.read(length) if length else None

        conn = http.client.HTTPConnection(UPSTREAM_HOST, UPSTREAM_PORT, timeout=30)
        try:
            conn.request(self.command, self.path, body=body, headers=headers)
            resp = conn.getresponse()
        finally:
            pass

        self.send_response(resp.status)
        for raw_k, raw_v in resp.getheaders():
            k = raw_k.decode('utf-8', 'replace') if isinstance(raw_k, bytes) else raw_k
            v = raw_v.decode('utf-8', 'replace') if isinstance(raw_v, bytes) else raw_v
            lk = k.lower()
            if lk in ('transfer-encoding', 'connection'):
                continue
            if lk == 'location':
                v = self._rewrite_location(v, orig_host, orig_proto)
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(resp.read())
        conn.close()

    def do_GET(self):
        self._proxy()

    def do_POST(self):
        self._proxy()

    def do_PUT(self):
        self._proxy()

    def do_PATCH(self):
        self._proxy()

    def do_DELETE(self):
        self._proxy()

    def log_message(self, format, *args):
        pass


if __name__ == '__main__':
    HTTPServer(('0.0.0.0', 4567), Proxy).serve_forever()
