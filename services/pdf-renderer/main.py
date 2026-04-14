from fastapi import FastAPI

app = FastAPI(title="dhg-pdf-renderer", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8014, reload=False)
