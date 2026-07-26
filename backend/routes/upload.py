"""
backend/routes/upload.py — ingest a lecture.

POST /upload  {"url": "<youtube or direct video url>"}
  -> indexes the video (upload -> understand -> index) and returns its video_id.
This is the first step: the frontend sends a link, gets back a video_id it then
uses for /chat. (File upload can be added later; URL covers the demo.)
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException
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
def upload(req: UploadRequest):
    """Ingest a lecture from a URL and return its indexed video_id."""
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="url is required")
    try:
        logger.info("ingesting %s", req.url)
        ref = retrieval.ingest(url=req.url.strip())
        return UploadResponse(video_id=ref.video_id,
                              title=getattr(ref, "title", "") or "",
                              length=float(getattr(ref, "length", 0) or 0))
    except Exception as e:
        logger.exception("ingest failed")
        raise HTTPException(status_code=500, detail=f"ingest failed: {e}")