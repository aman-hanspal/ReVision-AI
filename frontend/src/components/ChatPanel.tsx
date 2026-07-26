import React from "react";
import { useState } from "react";

const EXAMPLES = [
  "Full study pack on neural networks with an animated video",
  "Give me a summary reel of neural networks",
  "Make an animated explainer video on how digits are recognized",
  "Flashcards and cue cards on activations",
];

export default function ChatPanel({
  onSend, progress, thinking, disabled,
}: {
  onSend: (msg: string) => void;
  progress: string[];
  thinking: boolean;
  disabled: boolean;
}) {
  const [msg, setMsg] = useState("");

  function send(text: string) {
    if (!text.trim() || disabled) return;
    onSend(text.trim());
    setMsg("");
  }

  return (
    <div className="card chat">
      <div className="card-title">Ask ReVision</div>

      <div className="examples">
        {EXAMPLES.map((ex) => (
          <button key={ex} className="chip" onClick={() => send(ex)} disabled={disabled}>
            {ex}
          </button>
        ))}
      </div>

      <div className="trace">
        {progress.length === 0 && !thinking && (
          <div className="trace-empty">Pick an example or type a request…</div>
        )}
        {progress.map((p, i) => (
          <div key={i} className="trace-line">{p}</div>
        ))}
        {thinking && <div className="trace-line working">▸ working…</div>}
      </div>

      <div className="chat-input">
        <input placeholder="Ask for a clip, cards, a video…" value={msg}
          onChange={(e) => setMsg(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send(msg)}
          disabled={disabled} />
        <button onClick={() => send(msg)} disabled={disabled}>→</button>
      </div>
    </div>
  );
}