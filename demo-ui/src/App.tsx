import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";

import { Composer } from "./components/Composer";
import { Header } from "./components/Header";
import { Hero } from "./components/Hero";
import { MessageList } from "./components/MessageList";
import { PortfolioView } from "./components/PortfolioView";
import { Sidebar } from "./components/Sidebar";
import { Suggestions } from "./components/Suggestions";
import { useChat } from "./hooks/useChat";
import { getPortfolio } from "./lib/api";
import {
  loadConversations,
  newConversationId,
  saveConversations,
  titleFromQuery,
} from "./lib/conversations";
import type {
  ChatMode,
  ClientUser,
  Conversation,
  PortfolioAnalysis,
} from "./types";

const DEMO_USER: ClientUser = {
  id: "maria-lopez",
  name: "María López",
  riskProfile: "MODERATE",
};

const SUGGESTIONS = [
  "Analiza mi portafolio: ¿dónde tengo más concentrado mi dinero?",
  "¿Me afecta la situación con Jensen Huang?",
  "¿Qué es un ETF y cuánto cobran por retirar?",
  "¿Puedo retirar $5,000 hoy?",
];

const PORTFOLIO_TIMEOUT_MS = 15_000;

export default function App() {
  const user = DEMO_USER;
  const [mode, setMode] = useState<ChatMode>("agent");
  const [activeTab, setActiveTab] = useState<"chat" | "portfolio">("chat");
  const [portfolio, setPortfolio] = useState<PortfolioAnalysis | null>(null);
  const [portfolioLoading, setPortfolioLoading] = useState(false);
  const [portfolioError, setPortfolioError] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>(() =>
    loadConversations(),
  );
  const [activeId, setActiveId] = useState<string | null>(null);

  const { messages, isStreaming, send, stop, retry, loadMessages } = useChat();
  const endRef = useRef<HTMLDivElement | null>(null);

  const loadPortfolio = useCallback(async () => {
    setPortfolioLoading(true);
    setPortfolioError(null);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), PORTFOLIO_TIMEOUT_MS);
    try {
      setPortfolio(await getPortfolio(user.id, controller.signal));
    } catch {
      setPortfolioError("No pude cargar tu portafolio. Intenta de nuevo.");
    } finally {
      clearTimeout(timeout);
      setPortfolioLoading(false);
    }
  }, []);

  const openPortfolio = useCallback(() => {
    setActiveTab("portfolio");
    if (!portfolio && !portfolioLoading) void loadPortfolio();
  }, [portfolio, portfolioLoading, loadPortfolio]);

  const handleTabKeyDown = useCallback(
    (event: KeyboardEvent<HTMLElement>) => {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      event.preventDefault();
      const next = activeTab === "chat" ? "portfolio" : "chat";
      setActiveTab(next);
      document.getElementById(`tab-${next}`)?.focus();
    },
    [activeTab],
  );

  useEffect(() => {
    if (messages.length === 0) return;
    endRef.current?.scrollIntoView?.({
      behavior: isStreaming ? "auto" : "smooth",
      block: "end",
    });
  }, [isStreaming, messages]);

  useEffect(() => {
    if (!activeId || isStreaming) return;
    setConversations((current) => {
      const conversation = current.find((item) => item.id === activeId);
      if (!conversation || conversation.messages === messages) return current;
      const firstUser = messages.find((message) => message.role === "user");
      const next = current.map((item) =>
        item.id === activeId
          ? {
              ...item,
              messages,
              title:
                item.title ||
                (firstUser ? titleFromQuery(firstUser.content) : ""),
              updatedAt: new Date().toISOString(),
            }
          : item,
      );
      saveConversations(next);
      return next;
    });
  }, [activeId, isStreaming, messages]);

  const visibleConversations = conversations
    .filter((conversation) => conversation.userId === user.id)
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));

  const startConversation = useCallback(
    (text: string): string => {
      const now = new Date().toISOString();
      const conversation: Conversation = {
        id: newConversationId(),
        userId: user.id,
        title: titleFromQuery(text),
        mode,
        messages: [],
        createdAt: now,
        updatedAt: now,
      };
      setConversations((current) => {
        const next = [conversation, ...current];
        saveConversations(next);
        return next;
      });
      setActiveId(conversation.id);
      loadMessages([]);
      return conversation.id;
    },
    [loadMessages, mode, user],
  );

  const submit = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed) return;

      const active = conversations.find((item) => item.id === activeId);
      if (!active || active.mode !== mode) {
        startConversation(trimmed);
      }
      void send(trimmed, user.id, mode);
    },
    [activeId, conversations, mode, send, startConversation, user],
  );

  const selectConversation = useCallback(
    (conversation: Conversation) => {
      setActiveTab("chat");
      setActiveId(conversation.id);
      setMode(conversation.mode);
      loadMessages(conversation.messages);
    },
    [loadMessages],
  );

  const changeMode = useCallback(
    (nextMode: ChatMode) => {
      setMode(nextMode);
      setActiveTab("chat");
      if (activeId) {
        setActiveId(null);
        loadMessages([]);
      }
    },
    [activeId, loadMessages],
  );

  const newConversation = useCallback(() => {
    setActiveTab("chat");
    setActiveId(null);
    loadMessages([]);
  }, [loadMessages]);

  return (
    <div className="app">
      <Header user={user} mode={mode} onModeChange={changeMode} />

      <div className="shell">
        <Sidebar
          conversations={visibleConversations}
          activeId={activeId}
          disabled={isStreaming}
          onSelect={selectConversation}
          onNew={newConversation}
        />

        <main className="page">
          <nav
            className="view-tabs"
            role="tablist"
            aria-label="Vistas"
            onKeyDown={handleTabKeyDown}
          >
            <button
              type="button"
              role="tab"
              id="tab-chat"
              aria-controls="panel-chat"
              aria-selected={activeTab === "chat"}
              tabIndex={activeTab === "chat" ? 0 : -1}
              className={`view-tab${activeTab === "chat" ? " is-active" : ""}`}
              onClick={() => setActiveTab("chat")}
            >
              Chat
            </button>
            <button
              type="button"
              role="tab"
              id="tab-portfolio"
              aria-controls="panel-portfolio"
              aria-selected={activeTab === "portfolio"}
              tabIndex={activeTab === "portfolio" ? 0 : -1}
              className={`view-tab${activeTab === "portfolio" ? " is-active" : ""}`}
              onClick={openPortfolio}
            >
              Portafolio
            </button>
          </nav>

          {activeTab === "portfolio" ? (
            <div
              role="tabpanel"
              id="panel-portfolio"
              aria-labelledby="tab-portfolio"
            >
              <PortfolioView
                user={user}
                analysis={portfolio}
                loading={portfolioLoading}
                error={portfolioError}
                onRetry={loadPortfolio}
              />
            </div>
          ) : (
            <div role="tabpanel" id="panel-chat" aria-labelledby="tab-chat">
              <section
                className={`chat${messages.length === 0 ? " is-empty" : ""}`}
              >
                {messages.length === 0 && <Hero />}
                <div className="chat-mode-line">
                  <span className={`conversation-mode mode-${mode}`}>
                    {mode === "agent" ? "Agentic RAG" : "Naive RAG"}
                  </span>
                  <span className="chat-mode-hint">
                    {mode === "agent"
                      ? "Portafolio, herramientas y noticias de hoy"
                      : "Solo documentos del corpus"}
                  </span>
                </div>
                {messages.length === 0 && (
                  <Suggestions items={SUGGESTIONS} onPick={submit} />
                )}
                <MessageList
                  messages={messages}
                  onRetry={(message) => retry(message.request)}
                />
                <div ref={endRef} />
              </section>

              <div className="composer-dock">
                <Composer
                  disabled={isStreaming}
                  onSend={submit}
                  onStop={stop}
                />
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
