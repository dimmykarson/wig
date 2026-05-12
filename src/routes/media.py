import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from src.settings import settings

router = APIRouter()

UPLOAD_DIR = Path("/tmp/wig-uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

_ALLOWED = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "audio/mpeg", "audio/ogg", "audio/wav", "audio/mp4", "audio/aac",
    "video/mp4", "video/3gpp",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

_EXT = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif", "image/webp": ".webp",
    "audio/mpeg": ".mp3", "audio/ogg": ".ogg", "audio/wav": ".wav",
    "audio/mp4": ".m4a", "audio/aac": ".aac",
    "video/mp4": ".mp4", "video/3gpp": ".3gp",
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}


@router.post("/media/upload")
async def upload_media(file: UploadFile):
    ct = (file.content_type or "").split(";")[0].strip()
    if ct not in _ALLOWED:
        raise HTTPException(status_code=415, detail=f"Tipo não suportado: {ct}")

    ext = _EXT.get(ct, Path(file.filename or "file").suffix or ".bin")
    name = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_DIR / name
    dest.write_bytes(await file.read())

    base = settings.mock_base_url.rstrip("/")
    return {"url": f"{base}/media/{name}", "filename": file.filename or name, "type": ct}


@router.get("/media/{name}")
async def serve_media(name: str):
    path = UPLOAD_DIR / name
    if not path.exists():
        raise HTTPException(status_code=404)
    return FileResponse(path)
