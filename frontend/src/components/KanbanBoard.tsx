"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  closestCorners,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { KanbanColumn } from "@/components/KanbanColumn";
import { chatBoard, getBoard, putBoard } from "@/lib/boardApi";
import { createId, moveCard, type BoardData } from "@/lib/kanban";

type KanbanBoardProps = {
  username: string;
};

type ChatMessage = {
  role: "user" | "assistant";
  text: string;
};

const SAVE_ERROR_MESSAGE =
  "Could not save your latest change. Your board is still available locally.";
const LOAD_ERROR_MESSAGE = "Could not load your board. Please try again.";
const CHAT_ERROR_MESSAGE = "Could not send chat command. Please try again.";

const serializeBoard = (board: BoardData) => JSON.stringify(board);
const getChatHistoryStorageKey = (username: string) => `pm-chat-history:${username}`;

export const KanbanBoard = ({ username }: KanbanBoardProps) => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const [chatInput, setChatInput] = useState("");
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [isChatPending, setIsChatPending] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);

  const isMountedRef = useRef(true);
  const boardRef = useRef<BoardData | null>(null);
  const lastPersistedSignatureRef = useRef<string | null>(null);
  const saveInFlightRef = useRef(false);
  const loadAbortRef = useRef<AbortController | null>(null);
  const saveAbortRef = useRef<AbortController | null>(null);
  const chatAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      loadAbortRef.current?.abort();
      saveAbortRef.current?.abort();
      chatAbortRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    loadAbortRef.current?.abort();
    saveAbortRef.current?.abort();
    chatAbortRef.current?.abort();

    setBoard(null);
    setActiveCardId(null);
    setIsLoading(true);
    setLoadError(null);
    setSaveError(null);
    setIsSaving(false);

    setChatInput("");
    setIsChatPending(false);
    setChatError(null);
    setChatHistory(() => {
      if (typeof window === "undefined") {
        return [];
      }

      try {
        const raw = window.sessionStorage.getItem(getChatHistoryStorageKey(username));
        if (!raw) {
          return [];
        }

        const parsed = JSON.parse(raw) as ChatMessage[];
        if (!Array.isArray(parsed)) {
          return [];
        }

        return parsed.filter(
          (message) =>
            message &&
            (message.role === "user" || message.role === "assistant") &&
            typeof message.text === "string"
        );
      } catch {
        return [];
      }
    });

    boardRef.current = null;
    lastPersistedSignatureRef.current = null;
    saveInFlightRef.current = false;

    const loadController = new AbortController();
    loadAbortRef.current = loadController;

    const load = async () => {
      try {
        const loadedBoard = await getBoard(username, { signal: loadController.signal });
        if (!isMountedRef.current || loadController.signal.aborted) {
          return;
        }

        boardRef.current = loadedBoard;
        lastPersistedSignatureRef.current = serializeBoard(loadedBoard);
        setBoard(loadedBoard);
        setLoadError(null);
      } catch (error) {
        if (!isMountedRef.current || loadController.signal.aborted) {
          return;
        }

        setLoadError(
          error instanceof Error && error.message ? error.message : LOAD_ERROR_MESSAGE
        );
      } finally {
        if (!isMountedRef.current || loadController.signal.aborted) {
          return;
        }

        setIsLoading(false);
      }
    };

    void load();
  }, [username]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    try {
      window.sessionStorage.setItem(
        getChatHistoryStorageKey(username),
        JSON.stringify(chatHistory)
      );
    } catch {
      // Ignore storage write failures in restricted environments.
    }
  }, [chatHistory, username]);

  const persistLatestBoard = useCallback(async () => {
    if (saveInFlightRef.current) {
      return;
    }

    while (isMountedRef.current) {
      const latestBoard = boardRef.current;
      if (!latestBoard) {
        return;
      }

      const latestSignature = serializeBoard(latestBoard);
      if (latestSignature === lastPersistedSignatureRef.current) {
        return;
      }

      saveInFlightRef.current = true;
      setIsSaving(true);

      const saveController = new AbortController();
      saveAbortRef.current = saveController;

      try {
        await putBoard(username, latestBoard, { signal: saveController.signal });

        if (!isMountedRef.current || saveController.signal.aborted) {
          return;
        }

        lastPersistedSignatureRef.current = latestSignature;
        setSaveError(null);
      } catch (error) {
        if (!isMountedRef.current || saveController.signal.aborted) {
          return;
        }

        setSaveError(
          error instanceof Error && error.message ? error.message : SAVE_ERROR_MESSAGE
        );
        return;
      } finally {
        saveInFlightRef.current = false;
        if (isMountedRef.current) {
          setIsSaving(false);
        }
      }
    }
  }, [username]);

  const applyBoardUpdate = (update: (previous: BoardData) => BoardData) => {
    setBoard((previous) => {
      if (!previous) {
        return previous;
      }

      const next = update(previous);
      if (serializeBoard(next) === serializeBoard(previous)) {
        return previous;
      }

      boardRef.current = next;
      return next;
    });
  };

  useEffect(() => {
    if (!board || isLoading || loadError) {
      return;
    }

    if (serializeBoard(board) === lastPersistedSignatureRef.current) {
      return;
    }

    void persistLatestBoard();
  }, [board, isLoading, loadError, persistLatestBoard]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  const cardsById = useMemo(() => board?.cards ?? {}, [board?.cards]);

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!over || active.id === over.id) {
      return;
    }

    applyBoardUpdate((previous) => ({
      ...previous,
      columns: moveCard(previous.columns, active.id as string, over.id as string),
    }));
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    applyBoardUpdate((previous) => ({
      ...previous,
      columns: previous.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    }));
  };

  const handleAddCard = (columnId: string, title: string, details: string) => {
    const id = createId("card");
    applyBoardUpdate((previous) => ({
      ...previous,
      cards: {
        ...previous.cards,
        [id]: { id, title, details: details || "No details yet." },
      },
      columns: previous.columns.map((column) =>
        column.id === columnId ? { ...column, cardIds: [...column.cardIds, id] } : column
      ),
    }));
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    applyBoardUpdate((previous) => ({
      ...previous,
      cards: Object.fromEntries(Object.entries(previous.cards).filter(([id]) => id !== cardId)),
      columns: previous.columns.map((column) =>
        column.id === columnId
          ? {
            ...column,
            cardIds: column.cardIds.filter((id) => id !== cardId),
          }
          : column
      ),
    }));
  };

  const handleChatSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const message = chatInput.trim();
    if (!message || !boardRef.current || isChatPending) {
      return;
    }

    setChatInput("");
    setChatError(null);
    setIsChatPending(true);
    setChatHistory((previous) => [...previous, { role: "user", text: message }]);

    chatAbortRef.current?.abort();
    const chatController = new AbortController();
    chatAbortRef.current = chatController;

    try {
      const response = await chatBoard(username, message, { signal: chatController.signal });

      if (!isMountedRef.current || chatController.signal.aborted) {
        return;
      }

      setChatHistory((previous) => [
        ...previous,
        { role: "assistant", text: response.reply },
      ]);

      boardRef.current = response.board;
      lastPersistedSignatureRef.current = serializeBoard(response.board);
      setBoard(response.board);
      setSaveError(null);
    } catch (error) {
      if (!isMountedRef.current || chatController.signal.aborted) {
        return;
      }

      const messageText =
        error instanceof Error && error.message ? error.message : CHAT_ERROR_MESSAGE;
      setChatError(messageText);
      setChatHistory((previous) => [
        ...previous,
        { role: "assistant", text: messageText },
      ]);
    } finally {
      if (!isMountedRef.current || chatController.signal.aborted) {
        return;
      }

      setIsChatPending(false);
    }
  };

  const activeCard = activeCardId ? cardsById[activeCardId] : null;

  if (isLoading) {
    return (
      <main className="mx-auto flex min-h-screen max-w-[1500px] items-center justify-center px-6 py-12">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
          Loading board...
        </p>
      </main>
    );
  }

  if (loadError || !board) {
    return (
      <main className="mx-auto flex min-h-screen max-w-[1500px] items-center justify-center px-6 py-12">
        <p role="alert" className="text-sm font-semibold text-[var(--secondary-purple)]">
          {loadError ?? LOAD_ERROR_MESSAGE}
        </p>
      </main>
    );
  }

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1700px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Keep momentum visible. Rename columns, drag cards between stages, and capture
                quick notes without getting buried in settings.
              </p>
            </div>
            <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                Focus
              </p>
              <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                One board. Five columns. Zero clutter.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-4">
            {board.columns.map((column) => (
              <div
                key={column.id}
                className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                {column.title}
              </div>
            ))}
          </div>

          {saveError ? (
            <p role="alert" className="text-sm font-medium text-[var(--secondary-purple)]">
              {SAVE_ERROR_MESSAGE}
            </p>
          ) : null}

          {isSaving ? (
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
              Saving changes...
            </p>
          ) : null}
        </header>

        <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCorners}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <section className="grid gap-6 lg:grid-cols-5">
              {board.columns.map((column) => (
                <KanbanColumn
                  key={column.id}
                  column={column}
                  cards={column.cardIds.map((cardId) => board.cards[cardId])}
                  onRename={handleRenameColumn}
                  onAddCard={handleAddCard}
                  onDeleteCard={handleDeleteCard}
                />
              ))}
            </section>
            <DragOverlay>
              {activeCard ? (
                <div className="w-[260px]">
                  <KanbanCardPreview card={activeCard} />
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>

          <aside
            className="flex h-[720px] flex-col rounded-[28px] border border-[var(--stroke)] bg-white/90 p-5 shadow-[var(--shadow)]"
            data-testid="ai-sidebar"
          >
            <div className="mb-4">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                AI Assistant (Mock)
              </p>
              <p className="mt-2 text-sm text-[var(--gray-text)]">
                Try commands like: create card Draft agenda in Backlog, move card Plan release to
                Done, rename column Backlog to Ideas, delete card Ship update.
              </p>
            </div>

            <div
              className="flex-1 space-y-3 overflow-y-auto rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] p-3"
              data-testid="chat-history"
            >
              {chatHistory.length === 0 ? (
                <p className="text-sm text-[var(--gray-text)]">No messages yet.</p>
              ) : (
                chatHistory.map((message, index) => (
                  <div
                    key={`${message.role}-${index}`}
                    className={
                      message.role === "user"
                        ? "ml-8 rounded-xl bg-[var(--primary-blue)] px-3 py-2 text-sm text-white"
                        : "mr-8 rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)]"
                    }
                  >
                    {message.text}
                  </div>
                ))
              )}
            </div>

            {chatError ? (
              <p className="mt-3 text-sm font-medium text-[var(--secondary-purple)]" role="alert">
                {chatError}
              </p>
            ) : null}

            <form className="mt-4 space-y-3" onSubmit={handleChatSubmit}>
              <label htmlFor="chat-input" className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                Command
              </label>
              <textarea
                id="chat-input"
                value={chatInput}
                onChange={(event) => setChatInput(event.target.value)}
                rows={3}
                className="w-full rounded-2xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
                placeholder="Type a board command..."
              />
              <button
                type="submit"
                disabled={isChatPending}
                className="w-full rounded-xl bg-[var(--secondary-purple)] px-4 py-2 text-sm font-semibold text-white transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-70"
              >
                {isChatPending ? "Sending..." : "Send"}
              </button>
            </form>
          </aside>
        </div>
      </main>
    </div>
  );
};