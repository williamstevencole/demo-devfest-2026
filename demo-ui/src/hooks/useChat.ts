import { useCallback, useRef, useState } from "react";

import { applyEvent, finishRunningSteps } from "../lib/chatState";
import { streamChat } from "../lib/sse";
import type {
  ChatEvent,
  ChatMessage,
  ChatMode,
  ChatRequest,
} from "../types";

export const CHAT_TIMEOUT_MS = 180_000;
export const TIMEOUT_MESSAGE = "La consulta tardó demasiado. Intenta de nuevo.";
export const NETWORK_MESSAGE =
  "Se perdió la conexión con el agente. Revisa tu red e intenta de nuevo.";

function isNetworkError(error: unknown): boolean {
  return (
    error instanceof TypeError &&
    /networkerror|failed to fetch|load failed|network request failed|error in input stream/i.test(
      error.message,
    )
  );
}

interface UseChatOptions {
  timeoutMs?: number;
}

function isAbortError(error: unknown): boolean {
  return (
    typeof error === "object" &&
    error !== null &&
    (error as { name?: string }).name === "AbortError"
  );
}

function emptyMessage(
  id: string,
  role: ChatMessage["role"],
  request?: ChatRequest,
): ChatMessage {
  return {
    id,
    role,
    content: "",
    steps: [],
    streaming: role === "assistant",
    sources: [],
    disclaimerRequired: false,
    request,
  };
}

interface LastRequest {
  text: string;
  userId: string;
  mode: ChatMode;
}

export interface SendOptions {
  appendUser?: boolean;
}

export interface UseChatResult {
  messages: ChatMessage[];
  isStreaming: boolean;
  send: (
    text: string,
    userId: string,
    mode: ChatMode,
    options?: SendOptions,
  ) => Promise<void>;
  stop: () => void;
  retry: (request?: ChatRequest) => void;
  loadMessages: (messages: ChatMessage[]) => void;
}

export function useChat({
  timeoutMs = CHAT_TIMEOUT_MS,
}: UseChatOptions = {}): UseChatResult {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const streamingRef = useRef(false);
  const sequenceRef = useRef(0);
  const lastRequestRef = useRef<LastRequest | null>(null);
  const nextMessageId = useCallback((role: ChatMessage["role"]): string => {
    sequenceRef.current += 1;
    return `${role}-${Date.now()}-${sequenceRef.current}`;
  }, []);

  const applyToMessage = useCallback((id: string, event: ChatEvent) => {
    setMessages((current) =>
      current.map((message) =>
        message.id === id ? applyEvent(message, event) : message,
      ),
    );
  }, []);

  const closeMessage = useCallback(
    (id: string, status: "done" | "error", error?: string) => {
      setMessages((current) =>
        current.map((message) => {
          if (message.id !== id) return message;

          const finished = finishRunningSteps(message, status);
          return {
            ...finished,
            streaming: false,
            ...(error ? { error } : {}),
          };
        }),
      );
    },
    [],
  );

  const send = useCallback(
    async (
      text: string,
      userId: string,
      mode: ChatMode,
      options: SendOptions = {},
    ) => {
      const trimmed = text.trim();
      if (!trimmed || streamingRef.current) return;
      const appendUser = options.appendUser !== false;
      const history = messages
        .filter(
          (message) =>
            message.content.trim() &&
            !message.error &&
            !message.streaming,
        )
        .slice(-8)
        .map((message) => ({
          role: message.role,
          content: message.content,
        }));

      const request: ChatRequest = {
        user_id: userId,
        query: trimmed,
        mode,
        ...(history.length > 0 ? { history } : {}),
      };
      lastRequestRef.current = { text: trimmed, userId, mode };
      const assistantId = nextMessageId("assistant");
      const controller = new AbortController();
      abortRef.current = controller;
      streamingRef.current = true;
      let timedOut = false;
      const timeout = setTimeout(() => {
        timedOut = true;
        controller.abort();
      }, timeoutMs);

      const userMessage = {
        ...emptyMessage(nextMessageId("user"), "user"),
        content: trimmed,
      };
      setMessages((current) => [
        ...current,
        ...(appendUser ? [userMessage] : []),
        emptyMessage(assistantId, "assistant", request),
      ]);
      setIsStreaming(true);

      let terminal = false;
      try {
        for await (const event of streamChat(request, controller.signal)) {
          if (event.type === "done" || event.type === "error") terminal = true;
          applyToMessage(assistantId, event);
        }
        if (!terminal) closeMessage(assistantId, "done");
      } catch (error) {
        if (timedOut) {
          closeMessage(assistantId, "error", TIMEOUT_MESSAGE);
        } else if (controller.signal.aborted || isAbortError(error)) {
          closeMessage(assistantId, "done");
        } else {
          closeMessage(
            assistantId,
            "error",
            isNetworkError(error)
              ? NETWORK_MESSAGE
              : error instanceof Error
                ? error.message
                : "No se pudo completar la consulta.",
          );
        }
      } finally {
        clearTimeout(timeout);
        if (abortRef.current === controller) {
          abortRef.current = null;
          streamingRef.current = false;
          setIsStreaming(false);
        }
      }
    },
    [applyToMessage, closeMessage, messages, nextMessageId],
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    streamingRef.current = false;
    setIsStreaming(false);
    setMessages((current) =>
      current.map((message) =>
        message.streaming
          ? { ...finishRunningSteps(message, "stopped"), streaming: false }
          : message,
      ),
    );
  }, []);

  const retry = useCallback(
    (request?: ChatRequest) => {
      if (request) {
        void send(request.query, request.user_id, request.mode, {
          appendUser: false,
        });
        return;
      }
      const last = lastRequestRef.current;
      if (last) {
        void send(last.text, last.userId, last.mode, { appendUser: false });
      }
    },
    [send],
  );

  const loadMessages = useCallback((next: ChatMessage[]) => {
    abortRef.current?.abort();
    abortRef.current = null;
    streamingRef.current = false;
    setIsStreaming(false);
    setMessages(next);
  }, []);

  return {
    messages,
    isStreaming,
    send,
    stop,
    retry,
    loadMessages,
  };
}
