export type Flashcard = { front: string; back: string };

export type Display = {
  kind: string;
  topic?: string;
  // videos
  clip_url?: string;
  summary_reel_url?: string;
  learning_video_url?: string;
  single_clip_url?: string;   // from study_pack
  // study pack extras
  summary?: string | null;
  concept_image_url?: string | null;
  flashcards?: Flashcard[];
  cue_cards?: string[];
  // search
  query?: string;
  moments?: string[];
  // ingest
  video_id?: string;
  title?: string;
};

export type ProgressEvent = { type: "progress"; message: string; kind: string };
export type ResultEvent = { type: "result"; reply: string; displays: Display[] };
export type ErrorEvent = { type: "error"; message: string };
export type DoneEvent = { type: "done" };
export type StreamEvent = ProgressEvent | ResultEvent | ErrorEvent | DoneEvent;