"""
shared/models.py — data shapes for ReVision.

WHAT:  the plain data structures every layer passes around — a search hit, a
       clip, a flashcard, a summary, and the StudyPack that bundles them. Keeps
       the app speaking one vocabulary instead of raw dicts.
USED BY: retrieval.py, generate.py, the agent tools, and the backend routes.
KEY EXPORTS: TopicHit, Clip, Flashcard, CueCard, Summary, StudyPack,
             VideoRef, Slide.
NOTES: pure dataclasses — no network calls. from_shot() maps a VideoDB Shot
       (proven fields: video_id/start/end/text/search_score/stream_url) into
       our TopicHit so the rest of the app never touches the raw SDK object.
RUN:   python -m shared.models     # constructs samples + prints them
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Any, Dict


@dataclass
class VideoRef:
    """A lecture in the collection."""
    video_id: str
    title: str = ""
    length: float = 0.0
    source_url: Optional[str] = None      # YouTube/URL it came from, if any


@dataclass
class TopicHit:
    """A timestamped moment matching a query (mapped from a VideoDB Shot)."""
    video_id: str
    start: float
    end: float
    text: str = ""
    score: float = 0.0
    stream_url: Optional[str] = None      # per-shot clip URL if already generated

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    @classmethod
    def from_shot(cls, shot: Any) -> "TopicHit":
        """Map a VideoDB Shot into a TopicHit (defensive on optional fields)."""
        return cls(
            video_id=getattr(shot, "video_id", ""),
            start=float(getattr(shot, "start", 0.0) or 0.0),
            end=float(getattr(shot, "end", 0.0) or 0.0),
            text=getattr(shot, "text", "") or "",
            score=float(getattr(shot, "search_score", 0.0) or 0.0),
            stream_url=getattr(shot, "stream_url", None),
        )


@dataclass
class Clip:
    """A playable clip for a topic."""
    title: str
    stream_url: str
    start: float
    end: float
    thumbnail_url: Optional[str] = None

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


@dataclass
class Flashcard:
    """A question/answer study card."""
    front: str        # question / prompt
    back: str         # answer


@dataclass
class CueCard:
    """A short cue / key-point card (single-sided prompt)."""
    text: str


@dataclass
class Summary:
    """A grounded summary of a topic, with the source moments it came from."""
    text: str
    sources: List[TopicHit] = field(default_factory=list)


@dataclass
class Slide:
    """One slide of a learning video: an illustration + its narration."""
    image_prompt: str
    narration: str
    image_id: Optional[str] = None      # img-... once generated
    audio_id: Optional[str] = None      # a-...   once generated
    image_url: Optional[str] = None
    duration: float = 0.0               # seconds; = narration length once known


@dataclass
class StudyPack:
    """The full output for a topic: clip + summary + cards (+ optional video)."""
    topic: str
    video: VideoRef
    clip: Optional[Clip] = None                 # single tight "jump to this moment" clip
    summary_reel: Optional[Clip] = None         # CLIPPING feature: real lecture footage,
                                                #   key moments stitched. UI heading: "Summary Reel"
    summary: Optional[Summary] = None
    flashcards: List[Flashcard] = field(default_factory=list)
    cue_cards: List[CueCard] = field(default_factory=list)
    learning_video_url: Optional[str] = None    # SUMMARY VIDEO feature: FLUX images + TTS
                                                #   generated explainer. UI heading: "Summary Video"
    slides: List[Slide] = field(default_factory=list)
    concept_image_url: Optional[str] = None   # one illustration shown above the card deck (Option B)

    def to_dict(self) -> Dict[str, Any]:
        """JSON-serialisable form for API responses / the frontend."""
        return asdict(self)


if __name__ == "__main__":
    # smoke: construct samples and print them
    v = VideoRef(video_id="m-123", title="Neural Networks", length=1119.0,
                 source_url="https://youtu.be/aircAruvnKk")
    hit = TopicHit(video_id="m-123", start=102.7, end=157.4,
                   text="gradient descent...", score=0.87)
    pack = StudyPack(
        topic="gradient descent",
        video=v,
        clip=Clip(title="Gradient descent", stream_url="https://.../x.m3u8",
                  start=102.7, end=157.4),
        summary=Summary(text="Gradient descent minimises the loss...", sources=[hit]),
        flashcards=[Flashcard(front="What does gradient descent do?",
                              back="Minimises a loss function.")],
        cue_cards=[CueCard(text="Steps downhill along the negative gradient.")],
    )
    print("TopicHit.duration:", hit.duration)
    print("StudyPack keys:", list(pack.to_dict().keys()))
    print("flashcards:", pack.flashcards)
    print("models OK")