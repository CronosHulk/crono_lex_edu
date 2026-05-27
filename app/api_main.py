from __future__ import annotations

import uvicorn

from app.config import load_settings


def main() -> None:
    settings = load_settings()
    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host=settings.app_host,
        port=settings.app_port,
        reload=False,
        workers=settings.app_api_workers,
    )


if __name__ == "__main__":
    main()
