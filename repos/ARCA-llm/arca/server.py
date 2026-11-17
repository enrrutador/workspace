from __future__ import annotations

import argparse
import json
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from arca.agent_api import ARCAAgentBackend


class ARCAHTTPHandler(BaseHTTPRequestHandler):
    server_version = "ARCA/0.4"

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/v1/models":
            self._json(200, {"object": "list", "data": [{"id": "arca-native", "object": "model", "owned_by": "enrrutador", "capabilities": ["chat"]}]})
            return
        self._json(404, {"error": {"message": "not found", "type": "invalid_request_error"}})

    def _sse(self, completion_id: int, text: str, extra: dict[str, Any] | None = None) -> None:
        """OpenAI-compatible Server-Sent Events stream (what OpenCode/AI-SDK expect)."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        def chunk(delta: dict[str, Any], finish_reason: str | None = None) -> bytes:
            payload = {"id": f"arca-{completion_id}", "object": "chat.completion.chunk", "created": completion_id, "model": "arca-native", "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}]}
            return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")

        self.wfile.write(chunk({"role": "assistant"}))
        for piece in self._stream_pieces(text):
            self.wfile.write(chunk({"content": piece}))
            self.wfile.flush()
        final = chunk({}, finish_reason="stop")
        if extra:
            final = f"data: {json.dumps({**json.loads(final.decode('utf-8')[6:].strip()), 'arca': extra}, ensure_ascii=False)}\n\n".encode("utf-8")
        self.wfile.write(final)
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    @staticmethod
    def _stream_pieces(text: str, size: int = 80) -> list[str]:
        pieces = []
        for start in range(0, len(text), size):
            pieces.append(text[start : start + size])
        return pieces or [""]

    @staticmethod
    def _message_text(content: Any) -> str:
        """AI-SDK sends either plain strings or arrays of typed parts."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(part.get("text", "") for part in content if isinstance(part, dict) and isinstance(part.get("text"), str))
        return str(content)

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/v1/chat/completions":
            self._json(404, {"error": {"message": "not found", "type": "invalid_request_error"}})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length))
            messages = body.get("messages", [])
            user = next((self._message_text(message.get("content", "")) for message in reversed(messages) if message.get("role") == "user"), "")
            session_id = self.headers.get("X-ARCA-Session", body.get("user", "default"))
            result = self.server.backend.respond(str(user), str(session_id))
            now = int(time.time())
            arca_extra = {"success": result.success, "telemetry": result.telemetry, "trace": list(result.trace)}
            if body.get("stream"):
                self._sse(now, result.text, arca_extra)
                return
            self._json(200, {"id": f"arca-{now}", "object": "chat.completion", "created": now, "model": "arca-native", "choices": [{"index": 0, "message": {"role": "assistant", "content": result.text}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 0, "completion_tokens": len(result.text.encode("utf-8")), "total_tokens": len(result.text.encode("utf-8"))}, "arca": arca_extra})
        except Exception as exc:
            self._json(400, {"error": {"message": str(exc), "type": "invalid_request_error"}})

    def log_message(self, format: str, *args: Any) -> None:
        return


def backup_database(db: str | Path, backup_dir: str | Path = "backups", keep: int = 7) -> Path | None:
    """Consistent snapshot of the SQLite memory using the online backup API."""
    source = Path(db)
    if not source.exists():
        return None
    folder = Path(backup_dir); folder.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = folder / f"arca-{stamp}.db"
    with sqlite3.connect(source) as origin, sqlite3.connect(target) as copy:
        origin.backup(copy)
    snapshots = sorted(folder.glob("arca-*.db"))
    for stale in snapshots[:-keep]:
        stale.unlink(missing_ok=True)
    return target


def serve(model: str | Path, db: str | Path = "arca.db", host: str = "127.0.0.1", port: int = 8787,
          max_docs: int = 500, fetch_bytes: int = 500_000, answer_chars: int = 1200,
          max_web_docs: int = 3, backup_dir: str | Path = "backups", keep_backups: int = 7) -> None:
    if (snapshot := backup_database(db, backup_dir, keep_backups)) is not None:
        print(f"memory backup: {snapshot}")
    backend = ARCAAgentBackend(
        model,
        db,
        max_docs=max_docs,
        fetch_bytes=fetch_bytes,
        answer_chars=answer_chars,
        max_web_docs=max_web_docs,
        search_limit=5,
    )
    server = ThreadingHTTPServer((host, port), ARCAHTTPHandler)
    server.backend = backend
    print(f"ARCA OpenAI-compatible API listening on http://{host}:{port}/v1")
    print(f"limits: max_docs={max_docs} fetch={fetch_bytes}B/page answer={answer_chars}ch web_docs={max_web_docs}")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve ARCA for OpenCode and OpenAI-compatible clients")
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--db", default="arca.db")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--max-docs", type=int, default=500, help="maximum cached web documents kept in memory store")
    parser.add_argument("--fetch-bytes", type=int, default=500_000, help="per-page download budget in bytes")
    parser.add_argument("--answer-chars", type=int, default=1200, help="composed answer length cap")
    parser.add_argument("--max-web-docs", type=int, default=3, help="pages fetched per question")
    parser.add_argument("--backup-dir", default="backups")
    parser.add_argument("--keep-backups", type=int, default=7)
    args = parser.parse_args()
    serve(args.model, args.db, args.host, args.port, args.max_docs, args.fetch_bytes, args.answer_chars, args.max_web_docs, args.backup_dir, args.keep_backups)


if __name__ == "__main__":
    main()
