import React, { useRef, useState } from "react";
import { ingest, uploadFile } from "../lib/api";

export default function IngestPanel({
  videoId, setVideoId,
}: { videoId: string; setVideoId: (v: string) => void }) {
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [drag, setDrag] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function ingestUrl(link: string) {
    if (!link.trim()) return;
    setBusy(true); setStatus("Indexing link… this can take a minute");
    try {
      const r = await ingest(link.trim());
      setVideoId(r.video_id);
      setStatus(`Indexed · ${r.title || "lecture"} · ${Math.round(r.length)}s`);
    } catch (e: any) { setStatus(`Failed: ${e.message}`); }
    finally { setBusy(false); }
  }

  async function ingestFile(file: File) {
    setBusy(true); setStatus(`Uploading ${file.name}… indexing can take a few minutes`);
    try {
      const r = await uploadFile(file);
      setVideoId(r.video_id);
      setStatus(`Indexed · ${r.title || file.name} · ${Math.round(r.length)}s`);
    } catch (e: any) { setStatus(`Failed: ${e.message}`); }
    finally { setBusy(false); }
  }

  return (
    <div className="card">
      <div className="card-title">Lecture</div>

      <div
        className={"dropzone" + (drag ? " drag" : "")}
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault(); setDrag(false);
          const f = e.dataTransfer.files?.[0];
          if (f) ingestFile(f);
        }}
      >
        <span className="drop-ico">⤓</span>
        <span>{busy ? "Working…" : "Click to upload or drop a video"}</span>
        <input ref={fileRef} type="file" accept="video/*" hidden
          onChange={(e) => { const f = e.target.files?.[0]; if (f) ingestFile(f); }} />
      </div>

      <div className="ingest-row">
        <input placeholder="…or paste a YouTube link" value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ingestUrl(url)} />
        <button onClick={() => ingestUrl(url)} disabled={busy}>
          {busy ? "…" : "Index"}
        </button>
      </div>

      {status && <div className={"ingest-status" + (videoId ? " ok" : "")}>{status}</div>}
      {videoId && <div className="video-id">video_id: {videoId.slice(0, 22)}…</div>}
    </div>
  );
}