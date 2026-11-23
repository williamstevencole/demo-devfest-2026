import type { ChatEvent, ChatRequest } from "../types";
import { mapChatResponse, mapTraceStep } from "./api";

const EVENT_SEPARATOR = /\r?\n\r?\n/;
export const INVALID_SSE_MESSAGE = "El agente envió una respuesta inválida.";

interface WireEvent {
  type: "step" | "token" | "done" | "error";
  [key: string]: unknown;
}

function parseEvent(raw: string): ChatEvent | null {
  const data = raw
    .split(/\r?\n/)
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice("data:".length).trimStart())
    .join("\n");

  if (!data) return null;

  let event: WireEvent;
  try {
    event = JSON.parse(data) as WireEvent;
  } catch {
    throw new Error(INVALID_SSE_MESSAGE);
  }

  switch (event.type) {
    case "step":
      return {
        type: "step",
        ...mapTraceStep(
          event as unknown as Parameters<typeof mapTraceStep>[0],
        ),
      };
    case "token":
      return { type: "token", text: String(event.text ?? "") };
    case "done":
      return {
        type: "done",
        ...mapChatResponse(
          event as unknown as Parameters<typeof mapChatResponse>[0],
        ),
      };
    case "error":
      return {
        type: "error",
        message: String(event.message ?? "No se pudo completar la consulta."),
      };
    default:
      return null;
  }
}

export async function* streamChat(
  request: ChatRequest,
  signal?: AbortSignal,
): AsyncGenerator<ChatEvent> {
  const response = await fetch("/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  });

  if (!response.ok || !response.body) {
    throw new Error(`El servidor respondió ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const takeEvents = (final: boolean): ChatEvent[] => {
    const events: ChatEvent[] = [];

    for (;;) {
      const match = EVENT_SEPARATOR.exec(buffer);
      if (!match || match.index === undefined) break;

      const raw = buffer.slice(0, match.index);
      buffer = buffer.slice(match.index + match[0].length);

      const event = parseEvent(raw);
      if (event) events.push(event);
    }

    if (final && buffer.trim()) {
      const event = parseEvent(buffer);
      if (event) events.push(event);
      buffer = "";
    }

    return events;
  };

  for (;;) {
    const { done, value } = await reader.read();

    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    for (const event of takeEvents(false)) yield event;
  }

  buffer += decoder.decode();
  for (const event of takeEvents(true)) yield event;
}
