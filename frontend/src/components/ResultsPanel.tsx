import React from "react";
import type { Display } from "../types";
import ClipCard from "./ClipCard";
import { Flashcards, CueCards, SummaryCard } from "./StudyCard";

const ACCENTS = { clip: "#EEEDFE", reel: "#E1F5EE", video: "#FAECE7" };

export default function ResultsPanel({ displays, onTelegram }:
  { displays: Display[]; onTelegram: () => void }) {

  if (displays.length === 0) {
    return <div className="card results-empty">
      <div className="card-title">Study pack</div>
      <p className="muted">Results appear here once you ask ReVision for something.</p>
    </div>;
  }

  const videos: JSX.Element[] = [];
  const blocks: JSX.Element[] = [];

  displays.forEach((d, i) => {
    // videos (clip / reel / learning_video, or bundled in study_pack)
    if (d.kind === "clip" && d.clip_url)
      videos.push(<ClipCard key={"c"+i} label="Jump to moment" url={d.clip_url} accent={ACCENTS.clip} />);
    if (d.kind === "reel" && d.summary_reel_url)
      videos.push(<ClipCard key={"r"+i} label="Highlights" url={d.summary_reel_url} accent={ACCENTS.reel} />);
    if (d.kind === "learning_video" && d.learning_video_url)
      videos.push(<ClipCard key={"v"+i} label="AI explainer" url={d.learning_video_url} accent={ACCENTS.video} />);

    if (d.kind === "study_pack") {
      if (d.single_clip_url) videos.push(<ClipCard key={"sc"+i} label="Jump to moment" url={d.single_clip_url} accent={ACCENTS.clip} />);
      if (d.summary_reel_url) videos.push(<ClipCard key={"sr"+i} label="Highlights" url={d.summary_reel_url} accent={ACCENTS.reel} />);
      if (d.learning_video_url) videos.push(<ClipCard key={"sv"+i} label="AI explainer" url={d.learning_video_url} accent={ACCENTS.video} />);
      if (d.summary) blocks.push(<SummaryCard key={"sum"+i} text={d.summary} />);
      if (d.flashcards?.length) blocks.push(<Flashcards key={"fc"+i} cards={d.flashcards} image={d.concept_image_url} />);
      if (d.cue_cards?.length) blocks.push(<CueCards key={"cc"+i} items={d.cue_cards} />);
    }

    if (d.kind === "search" && d.moments?.length)
      blocks.push(
        <div className="card" key={"se"+i}>
          <div className="card-title">Moments · {d.query}</div>
          <ul className="cue-list">{d.moments.map((m, j) => <li key={j}>{m}</li>)}</ul>
        </div>
      );
  });

  return (
    <div className="results">
      <div className="card-title results-head">Study pack</div>
      {videos.length > 0 && <div className="video-grid">{videos}</div>}
      {blocks}
      <button className="tg-btn" onClick={onTelegram}>
        <span className="tg-ico">✈</span> Send to Telegram
      </button>
    </div>
  );
}