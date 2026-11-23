import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";

function sseResponse(payload: Record<string, unknown>): Response {
  const encoder = new TextEncoder();
  const body = `data: ${JSON.stringify({ type: "done", ...payload })}\n\n`;
  return new Response(
    new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(body));
        controller.close();
      },
    }),
    { status: 200, headers: { "Content-Type": "text/event-stream" } },
  );
}

function answerPayload(answer: string) {
  return {
    answer,
    mode: "agent",
    trace: { steps: [] },
    sources: [],
    disclaimer_required: false,
  };
}

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

describe("usuario de la demo", () => {
  it("usa a María por defecto, sin selector ni cédula", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        sseResponse(answerPayload("Hola, María.")),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(screen.getByText("María López")).toBeTruthy();

    const input = screen.getByLabelText("Mensaje");
    fireEvent.change(input, { target: { value: "¿Me afecta Jensen Huang?" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(await screen.findByText("Hola, María.")).toBeTruthy();

    const body = JSON.parse(String(fetchMock.mock.calls[0][1]?.body)) as {
      user_id: string;
    };
    expect(body.user_id).toBe("maria-lopez");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
