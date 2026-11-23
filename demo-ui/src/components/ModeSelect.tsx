import type { ChatMode } from "../types";

interface ModeSelectProps {
  value: ChatMode;
  onChange: (mode: ChatMode) => void;
}

export function ModeSelect({ value, onChange }: ModeSelectProps) {
  return (
    <label className="mode-select">
      <span className="mode-select-label">Modo</span>
      <select
        className="mode-select-input"
        value={value}
        aria-label="Modo de chat"
        onChange={(event) => onChange(event.target.value as ChatMode)}
      >
        <option value="agent">Agentic RAG</option>
        <option value="naive">Naive RAG</option>
      </select>
    </label>
  );
}
