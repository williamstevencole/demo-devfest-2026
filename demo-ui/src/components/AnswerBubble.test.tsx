import { render, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ChatMessage } from "../types";
import { AnswerBubble } from "./AnswerBubble";

function assistant(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: "a1",
    role: "assistant",
    content: "hola",
    steps: [],
    streaming: false,
    sources: [],
    disclaimerRequired: false,
    ...overrides,
  };
}

describe("AnswerBubble", () => {
  it("no renderiza HTML crudo del modelo", () => {
    const { container } = render(
      <AnswerBubble
        message={assistant({
          content: 'hola <script>alert("x")</script>',
        })}
      />,
    );
    expect(container.querySelector("script")).toBeNull();
  });

  it("renderiza Markdown GFM y el cursor mientras está en streaming", async () => {
    const { container } = render(
      <AnswerBubble
        message={assistant({
          content: "| a | b |\n| - | - |\n| 1 | 2 |",
          streaming: true,
        })}
      />,
    );
    expect(container.querySelector(".cursor")).not.toBeNull();
    await waitFor(() => expect(container.querySelector("table")).not.toBeNull());
  });

  it("revela el texto de una respuesta nueva de forma progresiva", async () => {
    const content = "Uno dos tres cuatro cinco";
    const { container, rerender } = render(
      <AnswerBubble message={assistant({ content, streaming: true })} />,
    );

    expect(container.textContent).not.toContain(content);
    await waitFor(() => expect(container.textContent).toContain(content), {
      timeout: 3000,
    });

    rerender(<AnswerBubble message={assistant({ content, streaming: false })} />);
    await waitFor(() => expect(container.querySelector(".cursor")).toBeNull(), {
      timeout: 3000,
    });
  });

  it("quita las citas .md del texto y deja las fuentes en la traza", () => {
    const { container } = render(
      <AnswerBubble
        message={assistant({
          content:
            "Un ETF es un fondo [glosario_de_mercado.md > ETF]. Se negocia como una acción [productos_disponibles.md > Acciones, ETFs y sectores].",
        })}
      />,
    );

    expect(container.textContent).toContain("Un ETF es un fondo.");
    expect(container.textContent).toContain("Se negocia como una acción.");
    expect(container.textContent).not.toContain(".md >");
  });

  it("muestra los datos que faltan cuando la respuesta es insuficiente", () => {
    const { container } = render(
      <AnswerBubble
        message={assistant({
          content: "No tengo el dato exacto.",
          insufficientData: true,
          missingData: ["la comisión exacta", "el plazo de liquidación"],
        })}
      />,
    );

    expect(container.querySelector(".answer-missing")?.textContent).toBe(
      "Falta: la comisión exacta; el plazo de liquidación",
    );
  });

  it("no renderiza una burbuja vacía sin error ni streaming", () => {
    const { container } = render(
      <AnswerBubble message={assistant({ content: "", streaming: false })} />,
    );
    expect(container.querySelector(".answer")).toBeNull();
  });
});
