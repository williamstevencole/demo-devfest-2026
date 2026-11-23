import type { TraceKind } from "../types";

export function StepGlyph({ kind }: { kind: TraceKind }) {
  switch (kind) {
    case "retrieval":
      return (
        <svg viewBox="0 0 24 24" width="11" height="11" aria-hidden="true">
          <circle cx="11" cy="11" r="6" />
          <path d="m20 20-4.5-4.5" />
        </svg>
      );
    case "web_search":
      return (
        <svg viewBox="0 0 24 24" width="11" height="11" aria-hidden="true">
          <circle cx="12" cy="12" r="8" />
          <path d="M4 12h16M12 4c2.4 2.2 3.6 4.9 3.6 8S14.4 17.8 12 20M12 4c-2.4 2.2-3.6 4.9-3.6 8S9.6 17.8 12 20" />
        </svg>
      );
    case "decision":
      return (
        <svg viewBox="0 0 24 24" width="11" height="11" aria-hidden="true">
          <path d="M6 4v6a4 4 0 0 0 4 4h8" />
          <path d="m15 11 3 3-3 3" />
          <path d="M6 20v-6" />
        </svg>
      );
    case "answer":
      return (
        <svg viewBox="0 0 24 24" width="11" height="11" aria-hidden="true">
          <path d="M12 20h9" />
          <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z" />
        </svg>
      );
    case "tool_call":
    default:
      return (
        <svg viewBox="0 0 24 24" width="11" height="11" aria-hidden="true">
          <ellipse cx="12" cy="5.5" rx="6.5" ry="2.8" />
          <path d="M5.5 5.5v13c0 1.5 2.9 2.8 6.5 2.8s6.5-1.3 6.5-2.8v-13" />
          <path d="M5.5 12c0 1.5 2.9 2.8 6.5 2.8s6.5-1.3 6.5-2.8" />
        </svg>
      );
  }
}
