"""Simple dev proxy: serves test_page.html at / and proxies /api/* to QwenPaw."""
import http.server
import urllib.request
import socketserver

PORT = 8091
BACKEND = "http://127.0.0.1:8088"
HTML_FILE = r"e:\workspace\github\QwenPaw\plugins\checkin\test_page.html"


class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(HTML_FILE, "rb") as f:
                self.wfile.write(f.read())
        elif self.path.startswith("/api/"):
            self._proxy("GET")
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path.startswith("/api/"):
            self._proxy("POST")
        else:
            self.send_error(404)

    def do_PUT(self):
        if self.path.startswith("/api/"):
            self._proxy("PUT")
        else:
            self.send_error(404)

    def do_DELETE(self):
        if self.path.startswith("/api/"):
            self._proxy("DELETE")
        else:
            self.send_error(404)

    def _proxy(self, method):
        url = BACKEND + self.path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else None
        headers = {}
        for key in ("Content-Type", "Authorization"):
            if key in self.headers:
                headers[key] = self.headers[key]
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            self.send_response(resp.status)
            for key, val in resp.getheaders():
                if key.lower() not in ("transfer-encoding", "connection"):
                    self.send_header(key, val)
            self.end_headers()
            self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_error(502, str(e))

    def log_message(self, fmt, *args):
        print(f"[proxy] {args[0]}")


class ReuseTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


with ReuseTCPServer(("", PORT), ProxyHandler) as httpd:
    print(f"Test page: http://127.0.0.1:{PORT}")
    httpd.serve_forever()
