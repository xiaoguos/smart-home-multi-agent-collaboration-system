from __future__ import annotations

import uvicorn

from config import load_settings


def main() -> None:
    settings = load_settings()
    uvicorn.run(
        "service:app",
        host=settings.service_host,
        port=settings.service_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
