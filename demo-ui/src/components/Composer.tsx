import { useState, type KeyboardEvent } from "react";

interface ComposerProps {
  disabled: boolean;
  onSend: (text: string) => void;
  onStop: () => void;
}

export function Composer({ disabled, onSend, onStop }: ComposerProps) {
  const [value, setValue] = useState("");

  const submit = () => {
    const text = value.trim();
    if (!text || disabled) return;

    onSend(text);
    setValue("");
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <form
      className="composer"
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <textarea
        className="composer-input"
        rows={1}
        value={value}
        disabled={disabled}
        placeholder="Pregunta sobre tu portafolio…"
        aria-label="Mensaje"
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
      />
      {disabled ? (
        <button type="button" className="composer-button stop" onClick={onStop}>
          Detener
        </button>
      ) : (
        <button
          type="submit"
          className="composer-button send"
          aria-label="Enviar"
          disabled={!value.trim()}
        >
          <svg viewBox="0 0 16 16" aria-hidden="true">
            <path d="M8 12V4M4.5 7.5 8 4l3.5 3.5" />
          </svg>
        </button>
      )}
    </form>
  );
}
