import { useEffect, useRef, useState } from "react";

const FRAMES_TO_FINISH = 36;

function requestFrame(callback: FrameRequestCallback): number {
  if (
    typeof window !== "undefined" &&
    typeof window.requestAnimationFrame === "function"
  ) {
    return window.requestAnimationFrame(callback);
  }
  return window.setTimeout(() => callback(Date.now()), 16);
}

function cancelFrame(handle: number): void {
  if (
    typeof window !== "undefined" &&
    typeof window.cancelAnimationFrame === "function"
  ) {
    window.cancelAnimationFrame(handle);
    return;
  }
  window.clearTimeout(handle);
}

export function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

interface TypewriterResult {
  displayed: string;
  typing: boolean;
}

/**
 * Reveal text progressively. The content can keep growing (naive streaming) or
 * arrive all at once (agent's final token); both finish in roughly the same
 * number of frames.
 */
export function useTypewriter(text: string, animate: boolean): TypewriterResult {
  const [displayed, setDisplayed] = useState(animate ? "" : text);
  const targetRef = useRef(text);
  const displayedRef = useRef(displayed);
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    targetRef.current = text;

    if (!animate) {
      displayedRef.current = text;
      setDisplayed(text);
      return;
    }

    if (!text.startsWith(displayedRef.current)) {
      const next = text.slice(
        0,
        Math.min(displayedRef.current.length, text.length),
      );
      displayedRef.current = next;
      setDisplayed(next);
    }

    if (frameRef.current !== null) return;

    const tick = () => {
      const target = targetRef.current;
      const current = displayedRef.current;

      if (current.length >= target.length) {
        frameRef.current = null;
        return;
      }

      const remaining = target.length - current.length;
      const step = Math.max(1, Math.ceil(remaining / FRAMES_TO_FINISH));
      const next = target.slice(0, current.length + step);
      displayedRef.current = next;
      setDisplayed(next);
      frameRef.current = requestFrame(tick);
    };

    frameRef.current = requestFrame(tick);
  }, [animate, text]);

  useEffect(
    () => () => {
      if (frameRef.current !== null) {
        cancelFrame(frameRef.current);
        frameRef.current = null;
      }
    },
    [],
  );

  return { displayed, typing: animate && displayed !== text };
}
