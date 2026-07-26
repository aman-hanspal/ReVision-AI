"""
backend/routes/upload.py — ingest a lecture (URL or file).

POST /upload        {"url": "..."}          -> ingest a YouTube/direct URL
POST /upload/file   (multipart file)        -> ingest an uploaded video file
Both index the video (upload -> understand -> index) and return its video_id.
"""
from __future__ import annotations

import logging
import os
import tempfile

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from shared import retrieval

logger = logging.getLogger("revision.api.upload")
router = APIRouter()


class UploadRequest(BaseModel):
    url: str


class UploadResponse(BaseModel):
    video_id: str
    title: str = ""
    length: float = 0.0


@router.post("/upload", response_model=UploadResponse)
def upload_url(req: UploadRequest):
    """Ingest a lecture from a URL."""
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="url is required")
    try:
        logger.info("ingesting url %s", req.url)
        ref = retrieval.ingest(url=req.url.strip())
        return _resp(ref)
    except Exception as e:
        logger.exception("url ingest failed")
        raise HTTPException(status_code=500, detail=f"ingest failed: {e}")


@router.post("/upload/file", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Ingest a lecture from an uploaded video file."""
    suffix = os.path.splitext(file.filename or "")[1] or ".mp4"
    tmp_path = None
    try:
        # save the upload to a temp file, then ingest by path
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            while chunk := await file.read(1024 * 1024):
                tmp.write(chunk)
        logger.info("ingesting uploaded file %s (%s)", file.filename, tmp_path)
        ref = retrieval.ingest(file_path=tmp_path)
        return _resp(ref)
    except Exception as e:
        logger.exception("file ingest failed")
        raise HTTPException(status_code=500, detail=f"file ingest failed: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def _resp(ref) -> UploadResponse:
    return UploadResponse(
        video_id=ref.video_id,
        title=getattr(ref, "title", "") or "",
        length=float(getattr(ref, "length", 0) or 0),
    )