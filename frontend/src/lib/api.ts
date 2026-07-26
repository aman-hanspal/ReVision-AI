import type { StreamEvent } from "../types";

export async function ingest(url: string): Promise<{ video_id: string; title: string; length: number }> {
  const res = await fetch("/upload", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) throw new Error(`ingest failed: ${res.status}`);
  return res.json();
}

/**
 * Stream the agent run. Calls onEvent for every SSE frame
 * (progress / result / error / done). Uses fetch + a stream reader
 * so we can POST a body (EventSource can't POST).
 */

export async function uploadFile(
  file: File
): Promise<{ video_id: string; title: string; length: number }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/upload/file", { method: "POST", body: form });
  if (!res.ok) throw new Error(`file upload failed: ${res.status}`);
  return res.json();
}

export async function chatStream(
  message: string,
  videoId: string,
  onEvent: (e: StreamEvent) => void
): Promise<void> {
  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, video_id: videoId }),
  });
  if (!res.body) throw new Error("no stream body");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line
    const frames = buffer.split("\n\n");
    buffer = frames.pop() || "";
    for (const frame of frames) {
      const line = frame.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;                       // skip keepalive comments
      const json = line.slice(5).trim();
      if (!json) continue;
      try {
        onEvent(JSON.parse(json) as StreamEvent);
      } catch {
        /* ignore malformed frame */
      }
    }
  }
}