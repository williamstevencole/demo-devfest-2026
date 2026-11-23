import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useChat } from "./useChat";

function sseResponse(chunks: string[]): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

const event = (payload: unknown) => `data: ${JSON.stringify(payload)}\n\n`;

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useChat", () => {
  it("envía usuario y modo, y aplica el done final", async () => {
    const fetchMock = vi.fn(async () =>
      sseResponse([
        event({
          type: "step",
          id: "s1",
          node: "load_portfolio",
          kind: "tool_call",
          title: "Portafolio de María López",
          detail: "4 posiciones",
          sources: [],
          status: "done",
          duration_ms: 42,
        }),
        event({ type: "token", text: "Tu exposición es 25.5%." }),
        event({
          type: "done",
          answer: "Tu exposición es 25.5%.",
          mode: "agent",
          trace: { steps: [] },
          sources: [],
          disclaimer_required: true,
        }),
      ]),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.send("¿Me afecta China?", "maria-lopez", "agent");
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/chat/stream",
      expect.objectContaining({
        body: JSON.stringify({
          user_id: "maria-lopez",
          query: "¿Me afecta China?",
          mode: "agent",
        }),
      }),
    );
    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[1]).toMatchObject({
      content: "Tu exposición es 25.5%.",
      disclaimerRequired: true,
      streaming: false,
    });
    expect(result.current.isStreaming).toBe(false);
  });

  it("incluye el historial en el segundo mensaje", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        sseResponse([
          event({
            type: "done",
            answer: "ok",
            mode: "agent",
            trace: { steps: [] },
            sources: [],
            disclaimer_required: false,
          }),
        ]),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.send("¿Qué es un ETF?", "", "agent");
    });
    await act(async () => {
      await result.current.send("dame ejemplos", "", "agent");
    });

    const secondBody = JSON.parse(
      String(fetchMock.mock.calls[1][1]?.body),
    ) as { history?: Array<{ role: string; content: string }> };
    expect(secondBody.history).toEqual([
      { role: "user", content: "¿Qué es un ETF?" },
      { role: "assistant", content: "ok" },
    ]);
  });

  it("retry repite usuario y modo del último envío sin duplicar el turno", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        sseResponse([
          event({
            type: "done",
            answer: "Hola",
            mode: "naive",
            trace: { steps: [] },
            sources: [],
            disclaimer_required: false,
          }),
        ]),
    );
    vi.stubGlobal("fetch", fetchMock);
    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.send("Hola", "maria-lopez", "naive");
    });
    await act(async () => {
      result.current.retry();
    });

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(fetchMock.mock.calls[1][1]).toEqual(
      expect.objectContaining({
        body: JSON.stringify({
          user_id: "maria-lopez",
          query: "Hola",
          mode: "naive",
          history: [
            { role: "user", content: "Hola" },
            { role: "assistant", content: "Hola" },
          ],
        }),
      }),
    );
    expect(
      result.current.messages.filter((message) => message.role === "user"),
    ).toHaveLength(1);
  });

  it("detener aborta el stream sin mostrar error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
        const encoder = new TextEncoder();
        let streamController: ReadableStreamDefaultController<Uint8Array>;
        const stream = new ReadableStream<Uint8Array>({
          start(controller) {
            streamController = controller;
            controller.enqueue(
              encoder.encode(
                event({
                  type: "step",
                  id: "s1",
                  node: "load_portfolio",
                  kind: "tool_call",
                  title: "Portafolio",
                  detail: "cargando",
                  sources: [],
                  status: "running",
                }),
              ),
            );
          },
        });
        init?.signal?.addEventListener("abort", () => streamController.close());
        return Promise.resolve(
          new Response(stream, {
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
          }),
        );
      }),
    );
    const { result } = renderHook(() => useChat());

    let pending: Promise<void>;
    act(() => {
      pending = result.current.send("Ping", "maria-lopez", "agent");
    });
    await waitFor(() =>
      expect(result.current.messages[1]?.steps).toHaveLength(1),
    );

    act(() => result.current.stop());
    await act(async () => {
      await pending;
    });

    expect(result.current.isStreaming).toBe(false);
    expect(result.current.messages[1]?.error).toBeUndefined();
    expect(result.current.messages[1]?.steps[0].status).toBe("stopped");
  });

  it("aborta por timeout y muestra un error claro", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
        let streamController: ReadableStreamDefaultController<Uint8Array>;
        const stream = new ReadableStream<Uint8Array>({
          start(controller) {
            streamController = controller;
            setTimeout(() => controller.close(), 200);
          },
        });
        init?.signal?.addEventListener("abort", () =>
          streamController.error(new DOMException("Aborted", "AbortError")),
        );
        return Promise.resolve(
          new Response(stream, {
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
          }),
        );
      }),
    );
    const { result } = renderHook(() => useChat({ timeoutMs: 30 }));

    await act(async () => {
      await result.current.send("Ping", "maria-lopez", "agent");
    });

    expect(result.current.isStreaming).toBe(false);
    expect(result.current.messages[1]).toMatchObject({
      streaming: false,
      error: "La consulta tardó demasiado. Intenta de nuevo.",
    });
  });

  it("un fallo de red muestra el error y cierra el streaming", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      }),
    );
    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.send("Ping", "maria-lopez", "agent");
    });

    expect(result.current.isStreaming).toBe(false);
    expect(result.current.messages[1]).toMatchObject({
      streaming: false,
      error: "network down",
    });
  });

  it("un corte de conexión de Firefox muestra un mensaje claro", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("NetworkError when attempting to fetch resource.");
      }),
    );
    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.send("Ping", "maria-lopez", "agent");
    });

    expect(result.current.messages[1]).toMatchObject({
      streaming: false,
      error:
        "Se perdió la conexión con el agente. Revisa tu red e intenta de nuevo.",
    });
  });

  it("el error de Firefox con el stream cortado también se traduce", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Error in input stream");
      }),
    );
    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.send("Ping", "maria-lopez", "agent");
    });

    expect(result.current.messages[1]).toMatchObject({
      streaming: false,
      error:
        "Se perdió la conexión con el agente. Revisa tu red e intenta de nuevo.",
    });
  });

  it("un evento SSE de error se muestra y cierra el streaming", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        sseResponse([
          event({ type: "error", message: "El portafolio no está disponible" }),
        ]),
      ),
    );
    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.send("Ping", "maria-lopez", "agent");
    });

    expect(result.current.isStreaming).toBe(false);
    expect(result.current.messages[1]).toMatchObject({
      streaming: false,
      error: "El portafolio no está disponible",
    });
  });

  it("cierra limpio si el stream termina sin done", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        sseResponse([event({ type: "token", text: "Respuesta parcial" })]),
      ),
    );
    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.send("Ping", "maria-lopez", "agent");
    });

    expect(result.current.isStreaming).toBe(false);
    expect(result.current.messages[1]).toMatchObject({
      content: "Respuesta parcial",
      streaming: false,
    });
    expect(result.current.messages[1]?.error).toBeUndefined();
  });
});
