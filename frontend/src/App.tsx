import React from "react";
import { useState } from "react";
import IngestPanel from "./components/IngestPanel";
import ChatPanel from "./components/ChatPanel";
import ResultsPanel from "./components/ResultsPanel";
import { chatStream } from "./lib/api";
import type { Display } from "./types";

const DEFAULT_VIDEO = "m-z-019f9824-94f6-7153-85b3-677a73ef3828"; // indexed demo lecture

export default function App() {
  const [videoId, setVideoId] = useState(DEFAULT_VIDEO);
  const [progress, setProgress] = useState<string[]>([]);
  const [displays, setDisplays] = useState<Display[]>([]);
  const [thinking, setThinking] = useState(false);

  async function handleSend(message: string) {
    setProgress([]); setDisplays([]); setThinking(true);
    try {
      await chatStream(message, videoId, (e) => {
        if (e.type === "progress") {
          setProgress((p) => [...p, e.message]);
        } else if (e.type === "result") {
          setDisplays(e.displays || []);
        } else if (e.type === "error") {
          setProgress((p) => [...p, "Error: " + e.message]);
        } else if (e.type === "done") {
          setThinking(false);
        }
      });
    } catch (err: any) {
      setProgress((p) => [...p, "Stream failed: " + err.message]);
    } finally {
      setThinking(false);
    }
  }

  function handleTelegram() {
    fetch("/telegram", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ displays }),
    }).then((r) => r.ok ? alert("Sent to Telegram") : alert("Telegram not configured yet"))
      .catch(() => alert("Telegram not configured yet"));
  }

  return (
    <div className="app">
      <header className="topbar">
        <span className="logo">ReVision <span className="logo-ai">AI</span></span>
        <span className="tagline">lectures → study packs</span>
      </header>

      <main className="grid">
        <section className="left">
          <IngestPanel videoId={videoId} setVideoId={setVideoId} />
          <ChatPanel onSend={handleSend} progress={progress} thinking={thinking}
            disabled={thinking || !videoId} />
        </section>
        <section className="right">
          <ResultsPanel displays={displays} onTelegram={handleTelegram} />
        </section>
      </main>
    </div>
  );
}