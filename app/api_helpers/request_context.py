from __future__ import annotations

from fastapi import Request

from app.auth.request_context import WebRequestContext


def build_request_context(request: Request) -> WebRequestContext:
    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    host = forwarded_host or request.headers.get("host")
    scheme = forwarded_proto or request.url.scheme
    api_origin = f"{scheme}://{host}" if host else None
    forwarded_for = request.headers.get("x-forwarded-for")
    client_ip = (forwarded_for.split(",", 1)[0].strip() if forwarded_for else None) or request.headers.get("x-real-ip")
    if client_ip is None and request.client is not None:
        client_ip = request.client.host
    return WebRequestContext(
        api_origin=api_origin,
        api_path=request.url.path,
        client_ip=client_ip,
        user_agent=request.headers.get("user-agent"),
    )
