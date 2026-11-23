import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import { CONVERSATIONS_STORAGE_KEY } from "../lib/conversations";
import { DisclaimerBadge } from "./DisclaimerBadge";

function sseResponse(answer: string): Response {
  const encoder = new TextEncoder();
  const body = `data: ${JSON.stringify({
    type: "done",
    answer,
    mode: "agent",
    trace: { steps: [] },
    sources: [],
    disclaimer_required: false,
  })}\n\n`;
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

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

describe("DisclaimerBadge", () => {
  it("muestra el badge de disclaimer", () => {
    render(<DisclaimerBadge visible />);
    expect(screen.getByText(/no es asesoría/i)).toBeTruthy();
  });

  it("no muestra nada sin recomendación", () => {
    const { container } = render(<DisclaimerBadge visible={false} />);
    expect(container.textContent).toBe("");
  });
});

describe("controles de la demo", () => {
  it("cambia el modo desde el combobox del header", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        sseResponse("Respuesta naive"),
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    const select = screen.getByLabelText("Modo de chat") as HTMLSelectElement;
    expect(select.value).toBe("agent");
    fireEvent.change(select, { target: { value: "naive" } });
    expect(select.value).toBe("naive");
    expect(screen.getAllByText("Naive RAG").length).toBeGreaterThan(0);

    const input = screen.getByLabelText("Mensaje");
    fireEvent.change(input, { target: { value: "¿Qué es un ETF?" } });
    fireEvent.keyDown(input, { key: "Enter" });

    expect(await screen.findByText("Respuesta naive")).toBeTruthy();
    const body = JSON.parse(String(fetchMock.mock.calls[0][1]?.body)) as {
      mode: string;
    };
    expect(body.mode).toBe("naive");
  });

  it("guarda la conversación con su badge de modo y permite abrir otra", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => sseResponse("Respuesta de María")),
    );
    render(<App />);

    const input = screen.getByLabelText("Mensaje");
    fireEvent.change(input, { target: { value: "Hola" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(await screen.findByText("Respuesta de María")).toBeTruthy();

    expect(screen.getAllByText("Hola").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Agentic RAG").length).toBeGreaterThan(0);

    fireEvent.click(
      screen.getByRole("button", { name: /Nueva conversación/ }),
    );
    expect(screen.queryByText("Respuesta de María")).toBeNull();
    expect(screen.getAllByText("Hola").length).toBeGreaterThan(0);
  });

  it("restaura el historial guardado al recargar", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => sseResponse("Respuesta persistida")),
    );
    const first = render(<App />);

    const input = screen.getByLabelText("Mensaje");
    fireEvent.change(input, { target: { value: "Hola persistente" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(await screen.findByText("Respuesta persistida")).toBeTruthy();

    await waitFor(() =>
      expect(
        window.localStorage.getItem(CONVERSATIONS_STORAGE_KEY),
      ).toContain("Hola persistente"),
    );

    first.unmount();
    render(<App />);

    expect(screen.getAllByText("Hola persistente").length).toBeGreaterThan(0);
    fireEvent.click(
      screen.getByRole("button", { name: /Hola persistente/ }),
    );
    expect(await screen.findByText("Respuesta persistida")).toBeTruthy();
  });

  it("muestra las sugerencias del guion y el composer del chat", () => {
    const { container } = render(<App />);

    expect(container.querySelector("img.brand-logo")).not.toBeNull();
    expect(
      screen.getByRole("button", { name: /Analiza mi portafolio/ }),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: /Jensen Huang/ })).toBeTruthy();
    expect(
      screen.getByRole("button", { name: /¿Qué es un ETF/ }),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: /5,000/ })).toBeTruthy();
    expect(
      screen.getByPlaceholderText("Pregunta sobre tu portafolio…"),
    ).toBeTruthy();
  });
});
