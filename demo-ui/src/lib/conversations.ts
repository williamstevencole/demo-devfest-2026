import type { Conversation } from "../types";

export const CONVERSATIONS_STORAGE_KEY = "devfest-broker-conversations-v1";
export const MAX_TITLE_LENGTH = 52;

function readJson<T>(key: string): T | null {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

export function loadConversations(): Conversation[] {
  const stored = readJson<Conversation[]>(CONVERSATIONS_STORAGE_KEY);
  if (!Array.isArray(stored)) return [];
  return stored.filter(
    (conversation) =>
      typeof conversation?.id === "string" &&
      typeof conversation?.userId === "string" &&
      Array.isArray(conversation?.messages),
  );
}

export function saveConversations(conversations: Conversation[]): void {
  try {
    window.localStorage.setItem(
      CONVERSATIONS_STORAGE_KEY,
      JSON.stringify(conversations),
    );
  } catch {
    // Ignore quota/private-mode failures.
  }
}

export function titleFromQuery(query: string): string {
  const clean = query.replace(/\s+/g, " ").trim();
  if (!clean) return "Nueva conversación";
  return clean.length > MAX_TITLE_LENGTH
    ? `${clean.slice(0, MAX_TITLE_LENGTH - 1)}…`
    : clean;
}

export function newConversationId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `conversation-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
