"""Tarayıcı OAuth akışları için: yetki adresini yazdırır, localhost'a dönen kodu yakalar."""
from __future__ import annotations

import secrets
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer


def capture_code(auth_url_base: str, params: dict, redirect_uri: str) -> str:
    state = secrets.token_urlsafe(16)
    url = auth_url_base + "?" + urllib.parse.urlencode({**params, "redirect_uri": redirect_uri, "state": state})
    print(f"Bu adresi tarayıcıda aç:\n{url}")
    result: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            result.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write("Tamam, terminale dönebilirsin.".encode())

        def log_message(self, *a):
            pass

    port = urllib.parse.urlparse(redirect_uri).port or 80
    server = HTTPServer(("0.0.0.0", port), Handler)
    while "code" not in result and "error" not in result:
        server.handle_request()
    server.server_close()
    if result.get("state") != state or "code" not in result:
        raise RuntimeError(f"Yetkilendirme başarısız: {result}")
    return result["code"]
