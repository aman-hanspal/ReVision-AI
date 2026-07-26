import React from "react";
import { useState } from "react";
import VideoPlayer from "./VideoPlayer";

export default function ClipCard({ label, url, accent }: { label: string; url: string; accent: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="card clip-card">
      {open ? (
        <VideoPlayer src={url} />
      ) : (
        <button className="clip-thumb" style={{ background: accent }} onClick={() => setOpen(true)}>
          <span className="clip-play">▶</span>
        </button>
      )}
      <div className="clip-label">{label}</div>
    </div>
  );
}