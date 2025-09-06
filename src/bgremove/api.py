from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
import uvicorn

from . import remove_bytes

api = FastAPI(title="bgremove", version="0.1.0")


@api.get("/health")
def health():
    return {"ok": True}


@api.post("/remove")
async def remove_endpoint(file: UploadFile = File(...), filename: Optional[str] = None):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    data = await file.read()
    try:
        cut = remove_bytes(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    # Return as PNG with alpha
    name = filename or Path(file.filename or "output").stem
    headers = {"Content-Disposition": f'inline; filename="{name}.png"'}
    return Response(content=cut, media_type="image/png", headers=headers)


def serve(host: str = "127.0.0.1", port: int = 8000):
    uvicorn.run(api, host=host, port=port)
