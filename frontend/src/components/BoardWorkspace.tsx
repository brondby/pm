"use client";

import { FormEvent, useEffect, useState } from "react";
import { BoardSwitcher } from "@/components/BoardSwitcher";
import { KanbanBoard } from "@/components/KanbanBoard";
import {
  createBoard,
  deleteBoard,
  listBoards,
  renameBoard,
  setBoardArchived,
  type BoardSummary,
} from "@/lib/boardsApi";

const LOAD_ERROR_MESSAGE = "Could not load your boards. Please try again.";

// Never auto-picked as the active board - an archived board must not
// silently become the default, and a fresh signup/new board is never
// archived, so this only ever excludes boards the user archived themselves.
const pickDefaultBoardId = (boards: BoardSummary[]): number | null =>
  boards.find((board) => !board.is_archived)?.id ?? null;

export const BoardWorkspace = () => {
  const [boards, setBoards] = useState<BoardSummary[] | null>(null);
  const [activeBoardId, setActiveBoardId] = useState<number | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [newBoardName, setNewBoardName] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);
  const [unarchiveError, setUnarchiveError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    void listBoards()
      .then((loadedBoards) => {
        if (!isMounted) {
          return;
        }
        setBoards(loadedBoards);
        setActiveBoardId(pickDefaultBoardId(loadedBoards));
      })
      .catch((error) => {
        if (!isMounted) {
          return;
        }
        setLoadError(
          error instanceof Error && error.message ? error.message : LOAD_ERROR_MESSAGE
        );
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const refreshBoards = async (): Promise<BoardSummary[]> => {
    const refreshed = await listBoards();
    setBoards(refreshed);
    return refreshed;
  };

  const handleCreateBoard = async (name: string) => {
    const created = await createBoard(name);
    await refreshBoards();
    // A newly created board is never archived, so it's always safe to select.
    setActiveBoardId(created.id);
  };

  const handleRenameBoard = async (boardId: number, name: string) => {
    await renameBoard(boardId, name);
    await refreshBoards();
  };

  const handleArchiveToggle = async (boardId: number, isArchived: boolean) => {
    await setBoardArchived(boardId, isArchived);
    const refreshed = await refreshBoards();

    // If the board that just got archived was the active one, an archived
    // board can never remain the active selection - fall back to the next
    // available non-archived board, or the empty state if there is none.
    if (isArchived && boardId === activeBoardId) {
      setActiveBoardId(pickDefaultBoardId(refreshed));
    }
  };

  const handleDeleteBoard = async (boardId: number) => {
    await deleteBoard(boardId);
    const refreshed = await refreshBoards();

    if (boardId === activeBoardId) {
      // Deliberate: never auto-create a replacement board here. If this was
      // the user's last board, they land in the empty state below and must
      // explicitly choose to create a new one.
      setActiveBoardId(pickDefaultBoardId(refreshed));
    }
  };

  const handleCreateFromEmptyState = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = newBoardName.trim();
    if (!trimmed) {
      return;
    }

    try {
      await handleCreateBoard(trimmed);
      setNewBoardName("");
      setCreateError(null);
    } catch (error) {
      setCreateError(
        error instanceof Error && error.message
          ? error.message
          : "Could not create board. Please try again."
      );
    }
  };

  const handleUnarchive = async (boardId: number) => {
    try {
      await handleArchiveToggle(boardId, false);
      setActiveBoardId(boardId);
      setUnarchiveError(null);
    } catch (error) {
      setUnarchiveError(
        error instanceof Error && error.message
          ? error.message
          : "Could not unarchive board. Please try again."
      );
    }
  };

  if (loadError) {
    return (
      <main className="mx-auto flex min-h-screen max-w-md items-center justify-center px-6 text-center">
        <p role="alert" className="text-sm font-semibold text-[var(--secondary-purple)]">
          {loadError}
        </p>
      </main>
    );
  }

  if (boards === null) {
    return (
      <main className="mx-auto flex min-h-screen items-center justify-center px-6">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
          Loading your boards...
        </p>
      </main>
    );
  }

  if (activeBoardId !== null) {
    return (
      <>
        <BoardSwitcher
          boards={boards}
          activeBoardId={activeBoardId}
          onSelect={setActiveBoardId}
          onCreate={handleCreateBoard}
          onRename={handleRenameBoard}
          onArchiveToggle={handleArchiveToggle}
          onDelete={handleDeleteBoard}
        />
        <KanbanBoard boardId={activeBoardId} />
      </>
    );
  }

  // First-class empty state: either the user has zero boards, or every
  // board they have is archived. Either way, a new board is only ever
  // created when the user explicitly asks for one here.
  const archivedBoards = boards.filter((board) => board.is_archived);

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-lg flex-col items-center justify-center gap-6 px-6 text-center">
      <div className="w-full rounded-3xl border border-[var(--stroke)] bg-white p-8 shadow-[var(--shadow)]">
        <h1 className="text-2xl font-semibold text-[var(--navy-dark)]">
          {archivedBoards.length > 0 ? "All your boards are archived" : "You don't have any boards yet"}
        </h1>
        <p className="mt-2 text-sm text-[var(--gray-text)]">
          {archivedBoards.length > 0
            ? "Unarchive one to keep working on it, or create a new board."
            : "Create your first board to get started."}
        </p>

        {archivedBoards.length > 0 ? (
          <ul className="mt-4 space-y-2 text-left" data-testid="archived-board-list">
            {archivedBoards.map((board) => (
              <li
                key={board.id}
                className="flex items-center justify-between rounded-xl border border-[var(--stroke)] px-3 py-2"
              >
                <span className="truncate text-sm font-medium text-[var(--navy-dark)]">
                  {board.name}
                </span>
                <button
                  type="button"
                  onClick={() => handleUnarchive(board.id)}
                  className="text-sm font-semibold text-[var(--primary-blue)] hover:underline"
                >
                  Unarchive
                </button>
              </li>
            ))}
          </ul>
        ) : null}

        {unarchiveError ? (
          <p role="alert" className="mt-3 text-sm text-[var(--secondary-purple)]">
            {unarchiveError}
          </p>
        ) : null}

        <form onSubmit={handleCreateFromEmptyState} className="mt-6 flex items-center gap-2">
          <input
            value={newBoardName}
            onChange={(event) => setNewBoardName(event.target.value)}
            placeholder="Board name"
            aria-label="Board name"
            className="min-w-0 flex-1 rounded-xl border border-[var(--stroke)] px-3 py-2 text-sm text-[var(--navy-dark)] focus:border-[var(--primary-blue)] focus:outline-none"
          />
          <button
            type="submit"
            className="rounded-xl bg-[var(--secondary-purple)] px-4 py-2 text-sm font-semibold text-white hover:opacity-90"
          >
            Create board
          </button>
        </form>

        {createError ? (
          <p role="alert" className="mt-3 text-sm text-[var(--secondary-purple)]">
            {createError}
          </p>
        ) : null}
      </div>
    </main>
  );
};
