import React from "react";
import { useState } from "react";
import type { Flashcard } from "../types";

export function Flashcards({ cards, image }: { cards: Flashcard[]; image?: string | null }) {
  return (
    <div className="card">
      <div className="card-title">Flashcards</div>
      {image && <img src={image} alt="concept" className="concept-img" />}
      <div className="flash-grid">
        {cards.map((c, i) => <FlashItem key={i} card={c} />)}
      </div>
    </div>
  );
}

function FlashItem({ card }: { card: Flashcard }) {
  const [flipped, setFlipped] = useState(false);
  return (
    <button className="flash" onClick={() => setFlipped((f) => !f)}>
      <div className="flash-side">{flipped ? "A" : "Q"}</div>
      <div className="flash-text">{flipped ? card.back : card.front}</div>
    </button>
  );
}

export function CueCards({ items }: { items: string[] }) {
  return (
    <div className="card">
      <div className="card-title">Cue cards</div>
      <ul className="cue-list">{items.map((t, i) => <li key={i}>{t}</li>)}</ul>
    </div>
  );
}

export function SummaryCard({ text }: { text: string }) {
  return (
    <div className="card">
      <div className="card-title">Summary</div>
      <p className="summary-text">{text}</p>
    </div>
  );
}