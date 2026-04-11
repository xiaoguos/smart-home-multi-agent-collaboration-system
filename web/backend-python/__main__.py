import uvicorn

import env


def main() -> None:
    uvicorn.run(
        "app:app",
        host=env.HOST,
        port=env.PORT,
        reload=env.DEBUG,
        log_level="info",
        http="h11",
    )


if __name__ == "__main__":
    main()
