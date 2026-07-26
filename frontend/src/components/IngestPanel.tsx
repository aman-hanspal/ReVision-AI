import React from "react";
import { useState } from "react";
import { ingest } from "../lib/api";

export default function IngestPanel({
  videoId, setVideoId,
}: { videoId: string; setVideoId: (v: string) => void }) {
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");

  async function doIngest(link: string) {
    if (!link.trim()) return;
    setBusy(true); setStatus("Indexing… this can take a minute");
    try {
      const r = await ingest(link.trim());
      setVideoId(r.video_id);
      setStatus(`Indexed · ${r.title || "lecture"} · ${Math.round(r.length)}s`);
    } catch (e: any) {
      setStatus(`Failed: ${e.message}`);
    } finally { setBusy(false); }
  }

  return (
    <div className="card">
      <div className="card-title">Lecture</div>

      <div className="dropzone"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); /* file upload = future; hint only */
          setStatus("File drop coming soon — paste a YouTube link below"); }}>
        <span className="drop-ico">⤓</span>
        <span>Click to upload or drop a video</span>
      </div>

      <div className="ingest-row">
        <input placeholder="…or paste a YouTube link" value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && doIngest(url)} />
        <button onClick={() => doIngest(url)} disabled={busy}>
          {busy ? "…" : "Index"}
        </button>
      </div>

      {status && <div className={"ingest-status" + (videoId ? " ok" : "")}>{status}</div>}
      {videoId && <div className="video-id">video_id: {videoId.slice(0, 22)}…</div>}
    </div>
  );
}