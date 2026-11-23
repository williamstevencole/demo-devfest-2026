interface SuggestionsProps {
  items: string[];
  onPick: (item: string) => void;
}

export function Suggestions({ items, onPick }: SuggestionsProps) {
  return (
    <div
      className="suggestions"
      role="group"
      aria-label="Preguntas sugeridas"
    >
      {items.map((item, index) => (
        <button
          key={item}
          type="button"
          className="chip"
          onClick={() => onPick(item)}
        >
          <span className="chip-index" aria-hidden="true">
            {String(index + 1).padStart(2, "0")}
          </span>
          <span>{item}</span>
        </button>
      ))}
    </div>
  );
}
