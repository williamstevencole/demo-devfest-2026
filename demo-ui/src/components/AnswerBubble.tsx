import { useRef } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import { prefersReducedMotion, useTypewriter } from "../hooks/useTypewriter";
import type { ChatMessage } from "../types";

interface AnswerBubbleProps {
  message: ChatMessage;
  onRetry?: () => void;
}

const markdownComponents: Components = {
  a: ({ node: _node, ...props }) => (
    <a {...props} target="_blank" rel="noopener noreferrer" />
  ),
};

const INLINE_CITATION = /\s*\[[^\]]*\.md\s*>[^\]]*\]/g;

export function stripInlineCitations(text: string): string {
  return text
    .replace(INLINE_CITATION, "")
    .replace(/[ \t]+([.,;:!?])/g, "$1")
    .replace(/[ \t]{2,}/g, " ")
    .trim();
}

export function AnswerBubble({ message, onRetry }: AnswerBubbleProps) {
  const animate = useRef(
    message.streaming && !prefersReducedMotion(),
  ).current;
  const renderedContent = stripInlineCitations(message.content);
  const { displayed, typing } = useTypewriter(renderedContent, animate);

  if (message.error) {
    return (
      <div className="answer-error" role="alert">
        <p>{message.error}</p>
        {onRetry && (
          <button type="button" className="retry" onClick={onRetry}>
            Reintentar
          </button>
        )}
      </div>
    );
  }

  if (!message.streaming && renderedContent.trim() === "") return null;

  const missing = message.missingData ?? [];
  const writing = message.streaming || typing;

  return (
    <div
      className="answer"
      aria-live={writing ? "off" : "polite"}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        skipHtml
        components={markdownComponents}
      >
        {displayed}
      </ReactMarkdown>
      {!writing &&
        (missing.length > 0 ? (
          <p className="answer-missing">Falta: {missing.join("; ")}</p>
        ) : (
          message.insufficientData && (
            <p className="answer-missing">
              No hay información suficiente para responder con seguridad.
            </p>
          )
        ))}
      {writing && <span className="cursor" aria-hidden="true" />}
    </div>
  );
}
