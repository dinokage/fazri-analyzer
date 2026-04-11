"""
Simple webhook listener for testing RTSP stream face-match payloads.
Runs on http://localhost:9000 by default.

Usage:
    python webhook_listener.py [port]
"""
import json
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer


PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9000


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            print(f"[{ts()}] Non-JSON payload received")
            self.send_response(400)
            self.end_headers()
            return

        self.send_response(200)
        self.end_headers()

        stream_id = payload.get("stream_id", "?")
        faces = payload.get("faces_found", 0)
        frames = payload.get("frames_processed", 0)
        matches = payload.get("matches", [])

        print(f"\n[{ts()}] stream={stream_id}  frames_processed={frames}  faces_found={faces}")
        for i, m in enumerate(matches, 1):
            dist = m.get("distance")
            rec_conf = m.get("recognition_confidence")
            det_conf = m.get("detector_confidence")
            print(
                f"  match {i}: name={m.get('img_name')}  "
                f"distance={dist:.4f}  "
                f"recognition_confidence={rec_conf}%  "
                f"detector_confidence={det_conf}"
            )
        if not matches:
            print("  (no matches)")

    def log_message(self, *args):
        pass  # suppress default access log noise


def ts():
    return datetime.now().strftime("%H:%M:%S")


if __name__ == "__main__":
    server = HTTPServer(("", PORT), WebhookHandler)
    print(f"Webhook listener running on http://localhost:{PORT}")
    print("Waiting for face-match events... (Ctrl+C to stop)\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
