"""Tiny frontend server with token generation endpoint.

Serves static files from the current directory and provides a /api/token
endpoint that generates LiveKit tokens with random room names (so each
connection gets a fresh room and the bridge worker always gets a new job).

No external dependencies — uses stdlib http.server + subprocess to call `lk`.
"""

import http.server
import json
import os
import random
import string
import subprocess
import sys


LK_API_KEY = os.environ.get("LIVEKIT_API_KEY", "devkey")
LK_API_SECRET = os.environ.get("LIVEKIT_API_SECRET", "secret")
PORT = int(os.environ.get("FRONTEND_PORT", "3000"))


def _generate_token(room: str, identity: str = "user1") -> str | None:
    """Generate a LiveKit token using the `lk` CLI."""
    result = subprocess.run(
        [
            "lk",
            "token",
            "create",
            "--api-key",
            LK_API_KEY,
            "--api-secret",
            LK_API_SECRET,
            "--join",
            "--room",
            room,
            "--identity",
            identity,
            "--valid-for",
            "24h",
        ],
        capture_output=True,
        text=True,
    )
    for line in result.stdout.splitlines():
        if "token:" in line.lower():
            return line.split()[-1]
    return None


def _random_room(voice: str = "tiffany") -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"voice-{voice}-{suffix}"


# Room configs: maps room name -> session config.
# Written by token endpoint, read by bridge via /api/room-config/<room>.
_room_configs: dict[str, dict] = {}


class TokenHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/token"):
            from urllib.parse import urlparse, parse_qs

            qs = parse_qs(urlparse(self.path).query)
            voice = qs.get("voice", ["tiffany"])[0]
            room = _random_room(voice)
            token = _generate_token(room)

            # Store session config for this room so the bridge can fetch it
            config = {
                "voice_id": voice,
                "temperature": float(qs.get("temperature", ["0.7"])[0]),
                "topP": float(qs.get("topP", ["0.9"])[0]),
                "endpointingSensitivity": qs.get("endpointingSensitivity", ["MEDIUM"])[0],
                "system_prompt": qs.get("systemPrompt", [""])[0],
            }
            _room_configs[room] = config

            if token:
                payload = json.dumps({"token": token, "room": room})
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(payload.encode())
            else:
                self.send_error(500, "Failed to generate token")
            return

        if self.path.startswith("/api/room-config/"):
            room = self.path.split("/api/room-config/")[1]
            config = _room_configs.pop(room, None)
            if config:
                payload = json.dumps(config)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(payload.encode())
            else:
                self.send_error(404, "No config for room")
            return

        return super().do_GET()

    def log_message(self, format, *args):
        # Suppress noisy static file logs; keep API logs
        if "/api/" in (args[0] if args else ""):
            super().log_message(format, *args)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = http.server.HTTPServer(("", PORT), TokenHandler)
    print(f"Frontend server on http://localhost:{PORT}")
    print(f"Token endpoint: http://localhost:{PORT}/api/token")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
