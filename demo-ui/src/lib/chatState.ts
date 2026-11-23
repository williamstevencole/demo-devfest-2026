import type {
  ChatEvent,
  ChatMessage,
  StepStatus,
  TraceStep,
} from "../types";

function upsertStep(steps: TraceStep[], step: TraceStep): TraceStep[] {
  const index = steps.findIndex((current) => current.id === step.id);

  if (index === -1) return [...steps, step];

  return steps.map((current, currentIndex) =>
    currentIndex === index ? step : current,
  );
}

export function finishRunningSteps(
  message: ChatMessage,
  status: Extract<StepStatus, "done" | "error" | "stopped">,
): ChatMessage {
  return {
    ...message,
    steps: message.steps.map((step) =>
      step.status === "running" ? { ...step, status } : step,
    ),
  };
}

export function applyEvent(message: ChatMessage, event: ChatEvent): ChatMessage {
  switch (event.type) {
    case "step": {
      const { type: _type, ...step } = event;
      return { ...message, steps: upsertStep(message.steps, step) };
    }

    case "token":
      return { ...message, content: message.content + event.text };

    case "done": {
      const finished = finishRunningSteps(message, "done");
      return {
        ...finished,
        content: event.answer,
        steps: event.trace.steps.length > 0 ? event.trace.steps : finished.steps,
        sources: event.sources,
        insufficientData: event.insufficientData === true,
        missingData: event.missingData ?? [],
        disclaimerRequired: event.disclaimerRequired,
        streaming: false,
        error: undefined,
      };
    }

    case "error":
      return {
        ...finishRunningSteps(message, "error"),
        error: event.message,
        streaming: false,
      };
  }
}
