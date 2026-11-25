"""OpenTutor 本地服务：标准库 http.server，零第三方依赖。"""
import json
import os
import sys
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import config
import curriculum
import memory
import model_provider
import store
import tutor

ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(ROOT, "static")
HOST = os.environ.get("OPEN_TUTOR_HOST", "127.0.0.1")
PORT = int(os.environ.get("OPEN_TUTOR_PORT", "8766"))


def provider():
    return model_provider.create_provider(config.get_config())


def ok(handler, data, code=200):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # 静默日志，避免泄露查询内容

    def do_OPTIONS(self):
        ok(self, {})

    def _body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(length) or "{}")
        except (ValueError, json.JSONDecodeError):
            return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path, q = parsed.path, parse_qs(parsed.query)
        if path == "/" or path == "/index.html":
            return self._static("index.html")
        if path.startswith("/static/"):
            return self._static(path[len("/static/"):])
        if path == "/api/meta":
            return ok(self, {
                "subjects": curriculum.SUBJECTS,
                "exams": curriculum.EXAMS,
                "config": config.public_config(),
                "progress": {
                    "messages": int(store.get_progress("messages", "0")),
                    "questions": int(store.get_progress("questions", "0")),
                    "streak": int(store.get_progress("streak", "0")),
                },
            })
        if path == "/api/sessions":
            return ok(self, store.list_sessions())
        if path == "/api/messages":
            return ok(self, store.get_messages(q.get("sid", [""])[0]))
        if path == "/api/artifacts":
            return ok(self, store.list_artifacts(q.get("sid", [""])[0] or None))
        if path == "/api/cards":
            return ok(self, store.list_cards(only_due=q.get("due", ["0"])[0] == "1"))
        return ok(self, {"error": "not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        b = self._body()

        if path == "/api/config":
            cfg = config.save_config(b)
            result, note = model_provider.test_provider(cfg)
            return ok(self, {"config": config.public_config(), "ok": result, "note": note})

        if path == "/api/test-model":
            result, note = model_provider.test_provider(config.get_config())
            return ok(self, {"ok": result, "note": note})

        if path == "/api/session/new":
            sid = "s-" + uuid.uuid4().hex[:10]
            store.create_session(b.get("title", "新会话"), b.get("subject", ""), sid)
            return ok(self, {"sid": sid})

        if path == "/api/session/delete":
            store.delete_session(b.get("sid", ""))
            return ok(self, {"ok": True})

        if path == "/api/chat":
            sid = b.get("sid", "")
            question = b.get("question", "").strip()
            if not sid or not question:
                return ok(self, {"error": "缺少 sid 或 question"}, 400)
            hist = store.get_messages(sid)
            subject = b.get("subject", "")
            reply = tutor.tutor_reply(provider(), hist, question, subject)
            store.add_message(sid, "user", question)
            store.add_message(sid, "assistant", reply)
            store.bump_counter("messages", 2)
            store.bump_counter("questions", 1)
            # 白板分步
            steps = tutor.parse_board(tutor.board_steps(provider(), reply, question))
            return ok(self, {"reply": reply, "steps": steps})

        if path == "/api/board":
            answer = b.get("answer", "")
            question = b.get("question", "")
            steps = tutor.parse_board(tutor.board_steps(provider(), answer, question))
            return ok(self, {"steps": steps})

        if path == "/api/artifact":
            sid = b.get("sid", "")
            kind = b.get("kind", "notes")
            hist = store.get_messages(sid)
            content = tutor.make_artifact(provider(), kind, hist)
            title = {"notes": "学习笔记", "solution": "解题过程", "flashcards": "抽认卡"}.get(kind, kind)
            version = store.add_artifact(sid, kind, title, content)
            if kind == "flashcards":
                for c in tutor.parse_flashcards(content):
                    store.add_card(c["question"], c["answer"], b.get("subject", ""))
            return ok(self, {"content": content, "version": version})

        if path == "/api/card/new":
            cid = store.add_card(b.get("question", ""), b.get("answer", ""), b.get("subject", ""))
            return ok(self, {"id": cid})

        if path == "/api/card/review":
            card_id = int(b.get("id", 0))
            quality = int(b.get("quality", 3))
            cards = {c["id"]: c for c in store.list_cards()}
            card = cards.get(card_id)
            if not card:
                return ok(self, {"error": "卡片不存在"}, 404)
            reps, interval = memory.next_schedule(card["reps"], quality)
            due = memory.due_date(interval)
            store.review_card(card_id, quality, reps, interval, due)
            return ok(self, {"reps": reps, "interval": interval, "due_at": due})

        if path == "/api/card/delete":
            store.delete_card(int(b.get("id", 0)))
            return ok(self, {"ok": True})

        if path == "/api/question/bank":
            code = b.get("code", "MATH")
            return ok(self, curriculum.SAMPLE_QUESTIONS.get(code, []))

        if path == "/api/streak":
            v = store.bump_counter("streak", 1)
            return ok(self, {"streak": v})

        return ok(self, {"error": "not found"}, 404)

    def _static(self, name):
        # 只允许访问 static 目录内的文件，防目录穿越
        name = os.path.basename(name)
        full = os.path.join(STATIC, name)
        if not os.path.isfile(full):
            full = os.path.join(STATIC, "index.html")
        ext = os.path.splitext(full)[1]
        ctype = {".html": "text/html", ".js": "application/javascript",
                 ".css": "text/css", ".png": "image/png", ".svg": "image/svg+xml"}.get(ext, "text/plain")
        with open(full, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    store.init()
    print("OpenTutor running at http://%s:%d/" % (HOST, PORT))
    print("Provider:", config.get_config()["provider"])
    try:
        ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")


if __name__ == "__main__":
    main()
