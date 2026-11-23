import type { Conversation } from "../types";

interface SidebarProps {
  conversations: Conversation[];
  activeId: string | null;
  disabled?: boolean;
  onSelect: (conversation: Conversation) => void;
  onNew: () => void;
}

const GROUP_ORDER = ["Hoy", "Ayer", "Últimos 7 días", "Anteriores"];

function modeLabel(mode: Conversation["mode"]): string {
  return mode === "agent" ? "Agentic RAG" : "Naive RAG";
}

function dayStart(date: Date): number {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
}

function groupLabel(updatedAt: string): string {
  const date = new Date(updatedAt);
  if (Number.isNaN(date.getTime())) return "Anteriores";
  const days = Math.round((dayStart(new Date()) - dayStart(date)) / 86_400_000);
  if (days <= 0) return "Hoy";
  if (days === 1) return "Ayer";
  if (days < 7) return "Últimos 7 días";
  return "Anteriores";
}

function groupConversations(
  conversations: Conversation[],
): { label: string; items: Conversation[] }[] {
  const groups = new Map<string, Conversation[]>();
  for (const conversation of conversations) {
    const label = groupLabel(conversation.updatedAt);
    groups.set(label, [...(groups.get(label) ?? []), conversation]);
  }
  return GROUP_ORDER.filter((label) => groups.has(label)).map((label) => ({
    label,
    items: groups.get(label) ?? [],
  }));
}

export function Sidebar({
  conversations,
  activeId,
  disabled = false,
  onSelect,
  onNew,
}: SidebarProps) {
  const groups = groupConversations(conversations);

  return (
    <aside className="sidebar" aria-label="Historial de conversaciones">
      <button
        type="button"
        className="sidebar-new"
        onClick={onNew}
        disabled={disabled}
      >
        <span className="sidebar-new-icon" aria-hidden="true">
          <svg viewBox="0 0 16 16">
            <path d="M8 3v10M3 8h10" />
          </svg>
        </span>
        Nueva conversación
      </button>

      <div className="sidebar-head">
        <span className="sidebar-title">Conversaciones</span>
      </div>

      {conversations.length === 0 ? (
        <p className="sidebar-empty">
          Aún no hay conversaciones. Haz la primera pregunta.
        </p>
      ) : (
        <nav className="conversation-groups">
          {groups.map((group) => (
            <section key={group.label} className="conversation-group">
              <h2 className="conversation-group-title">{group.label}</h2>
              <ol className="conversation-list">
                {group.items.map((conversation) => {
                  const active = conversation.id === activeId;
                  return (
                    <li key={conversation.id}>
                      <button
                        type="button"
                        className={`conversation${active ? " is-active" : ""}`}
                        aria-current={active ? "true" : undefined}
                        onClick={() => onSelect(conversation)}
                        disabled={disabled && !active}
                      >
                        <span className="conversation-title">
                          {conversation.title || "Nueva conversación"}
                        </span>
                        <span
                          className={`conversation-mode mode-${conversation.mode}`}
                        >
                          {modeLabel(conversation.mode)}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ol>
            </section>
          ))}
        </nav>
      )}
    </aside>
  );
}
