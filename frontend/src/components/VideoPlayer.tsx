import React from "react";
import { useEffect, useRef } from "react";
import Hls from "hls.js";

export default function VideoPlayer({ src }: { src: string }) {
  const ref = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = ref.current;
    if (!video || !src) return;
    // native HLS (Safari) vs hls.js (Chrome/Firefox)
    if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = src;
    } else if (Hls.isSupported()) {
      const hls = new Hls();
      hls.loadSource(src);
      hls.attachMedia(video);
      return () => hls.destroy();
    } else {
      video.src = src; // last resort
    }
  }, [src]);

  return (
    <video ref={ref} controls playsInline
      style={{ width: "100%", borderRadius: 10, background: "#000", aspectRatio: "16/9" }} />
  );
}