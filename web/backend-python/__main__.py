import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

import uvicorn


def main() -> None:
    uvicorn.run(
        "app:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "3000")),
        reload=os.getenv("DEBUG", "false").lower() in ("1", "true", "yes"),
        log_level="info",
        http="h11",
    )


if __name__ == "__main__":
    main()
