import type { ChatMessage } from "../types";
import { AgentTrace } from "./AgentTrace";
import { AnswerBubble } from "./AnswerBubble";
import { DisclaimerBadge } from "./DisclaimerBadge";

interface MessageListProps {
  messages: ChatMessage[];
  onRetry?: (message: ChatMessage) => void;
}

export function MessageList({ messages, onRetry }: MessageListProps) {
  return (
    <div
      className="message-list"
      aria-busy={messages.some((message) => message.streaming)}
    >
      {messages.map((message) =>
        message.role === "user" ? (
          <div key={message.id} className="user-row">
            <div className="user-bubble">{message.content}</div>
          </div>
        ) : (
          <div key={message.id} className="assistant-row">
            {message.streaming &&
              message.steps.length === 0 &&
              message.content.trim() === "" && (
                <div className="assistant-thinking" role="status">
                  <span className="thinking-mark" aria-hidden="true" />
                  Consultando al agente…
                </div>
              )}
            <AgentTrace
              steps={message.steps}
              sources={message.sources}
              insufficientData={message.insufficientData}
            />
            <AnswerBubble
              message={message}
              onRetry={onRetry ? () => onRetry(message) : undefined}
            />
            <DisclaimerBadge visible={message.disclaimerRequired} />
          </div>
        ),
      )}
    </div>
  );
}
