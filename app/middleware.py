import time

from starlette.types import ASGIApp, Receive, Scope, Send

from .database import SessionLocal
from .models import RequestLog
from .security import client_from_token

MAX_BODY = 20000
LOG_PREFIXES = ("/auth", "/frames", "/translation", "/prediction", "/session", "/classes")


def _should_log(path: str) -> bool:
    return any(path.startswith(p) for p in LOG_PREFIXES)


def _header(scope: Scope, name: bytes) -> str | None:
    for k, v in scope.get("headers", []):
        if k == name:
            return v.decode("latin-1")
    return None


class RequestLogMiddleware:
    """Pure-ASGI middleware: istek/yanıt gövdelerini 'tee'leyerek loglar.

    BaseHTTPMiddleware'in gövde tüketme sorununu yaşamamak için saf ASGI yazıldı;
    receive/send sarmalanır ama akış değiştirilmez."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not _should_log(scope.get("path", "")):
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        req_body = bytearray()
        resp_body = bytearray()
        status_holder = {"code": 0}

        async def receive_wrapper():
            message = await receive()
            if message["type"] == "http.request":
                chunk = message.get("body", b"")
                if chunk and len(req_body) < MAX_BODY:
                    req_body.extend(chunk[: MAX_BODY - len(req_body)])
            return message

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_holder["code"] = message["status"]
            elif message["type"] == "http.response.body":
                chunk = message.get("body", b"")
                if chunk and len(resp_body) < MAX_BODY:
                    resp_body.extend(chunk[: MAX_BODY - len(resp_body)])
            await send(message)

        try:
            await self.app(scope, receive_wrapper, send_wrapper)
        finally:
            latency_ms = (time.perf_counter() - start) * 1000.0
            self._write_log(scope, status_holder["code"], latency_ms, bytes(req_body), bytes(resp_body))

    def _write_log(self, scope, status_code, latency_ms, req_body, resp_body):
        db = SessionLocal()
        try:
            authorization = _header(scope, b"authorization")
            client = client_from_token(db, authorization)
            ip = None
            if scope.get("client"):
                ip = scope["client"][0]
            log = RequestLog(
                client_id=client.id if client else None,
                team_name=client.team_name if client else None,
                method=scope.get("method", ""),
                path=scope.get("path", ""),
                status_code=status_code,
                latency_ms=round(latency_ms, 2),
                ip_address=ip,
                request_body=_decode(req_body),
                response_body=_decode(resp_body),
            )
            db.add(log)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


def _decode(data: bytes) -> str | None:
    if not data:
        return None
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return None
