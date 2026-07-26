"""
backend/routes/telegram.py — push a study pack to Telegram.

POST /telegram  {"displays": [ ... ]}   (the displays array from a /chat result)
  -> sends the summary + links + cards to the configured Telegram chat.
Soft-fails: if Telegram isn't configured, returns ok=false with a friendly message
(the frontend shows "not configured yet") — never a 500.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any

from shared import telegram_service

router = APIRouter()


class TelegramRequest(BaseModel):
    displays: List[Dict[str, Any]] = []


@router.post("/telegram")
def telegram(req: TelegramRequest):
    ok, message = telegram_service.send_study_pack(req.displays)
    return {"ok": ok, "message": message}