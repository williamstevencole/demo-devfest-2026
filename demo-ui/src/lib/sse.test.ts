import { afterEach, describe, expect, it, vi } from "vitest";

import { streamChat } from "./sse";

function responseWith(chunks: string[]): Response {
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

const params = {
  user_id: "maria-lopez",
  query: "hola",
  mode: "agent" as const,
};

async function collect(chunks: string[]) {
  vi.stubGlobal("fetch", vi.fn(async () => responseWith(chunks)));
  const events = [];
  for await (const event of streamChat(params)) events.push(event);
  return events;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("streamChat", () => {
  it("envía usuario, consulta y modo al endpoint SSE", async () => {
    const fetchMock = vi.fn(async () => responseWith([]));
    vi.stubGlobal("fetch", fetchMock);

    for await (const _event of streamChat(params)) {
      // Consume the empty stream.
    }

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/chat/stream",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      }),
    );
  });

  it("parsea eventos partidos entre chunks", async () => {
    const events = await collect([
      'data: {"type":"token","text":"ho',
      'la"}\n\n',
    ]);
    expect(events).toEqual([{ type: "token", text: "hola" }]);
  });

  it("mapea duration_ms y disclaimer_required en el borde", async () => {
    const events = await collect([
      'data: {"type":"step","id":"s1","node":"load_portfolio","kind":"tool_call","title":"Portafolio","detail":"4 posiciones","sources":[],"status":"done","duration_ms":42}\n\n',
      'data: {"type":"done","answer":"Hola","mode":"agent","trace":{"steps":[]},"sources":[],"disclaimer_required":true}\n\n',
    ]);

    expect(events[0]).toMatchObject({
      type: "step",
      id: "s1",
      durationMs: 42,
    });
    expect(events[1]).toMatchObject({
      type: "done",
      disclaimerRequired: true,
    });
    expect(events[1]).not.toHaveProperty("disclaimer_required");
  });

  it("parsea varios eventos en un mismo chunk y el último sin delimitador", async () => {
    const events = await collect([
      'data: {"type":"step","id":"s1","node":"load_portfolio","kind":"tool_call","title":"Portafolio","detail":"cargando","sources":[],"status":"running"}\n\n',
      'data: {"type":"token","text":"ho"}\n\n',
      'data: {"type":"done","answer":"Hola","mode":"agent","trace":{"steps":[]},"sources":[],"disclaimer_required":false}',
    ]);
    expect(events).toHaveLength(3);
    expect(events[2]).toMatchObject({
      type: "done",
      answer: "Hola",
      disclaimerRequired: false,
    });
  });

  it("lanza error si la respuesta HTTP no es correcta", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("boom", { status: 500 })),
    );
    const events = streamChat(params);
    await expect(events.next()).rejects.toThrow(/500/);
  });

  it("lanza un error tipado si un evento SSE no es JSON válido", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => responseWith(["data: esto-no-es-json\n\n"])),
    );
    const events = streamChat(params);
    await expect(events.next()).rejects.toThrow(
      "El agente envió una respuesta inválida.",
    );
  });
});
