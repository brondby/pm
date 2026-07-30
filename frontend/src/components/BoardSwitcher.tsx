"use client";

import { FormEvent, useState } from "react";
import type { BoardSummary } from "@/lib/boardsApi";

type BoardSwitcherProps = {
  boards: BoardSummary[];
  activeBoardId: number;
  onSelect: (boardId: number) => void;
  onCreate: (name: string) => Promise<void>;
  onRename: (boardId: number, name: string) => Promise<void>;
  onArchiveToggle: (boardId: number, isArchived: boolean) => Promise<void>;
  onDelete: (boardId: number) => Promise<void>;
};

export const BoardSwitcher = ({
  boards,
  activeBoardId,
  onSelect,
  onCreate,
  onRename,
  onArchiveToggle,
  onDelete,
}: BoardSwitcherProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameInput, setRenameInput] = useState("");
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null);
  const [newBoardName, setNewBoardName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const activeBoard = boards.find((board) => board.id === activeBoardId);

  const closeAllSubMenus = () => {
    setRenamingId(null);
    setPendingDeleteId(null);
    setError(null);
  };

  const handleSelect = (boardId: number) => {
    onSelect(boardId);
    setIsOpen(false);
    closeAllSubMenus();
  };

  const startRename = (board: BoardSummary) => {
    setRenamingId(board.id);
    setRenameInput(board.name);
    setPendingDeleteId(null);
  };

  const submitRename = async (event: FormEvent<HTMLFormElement>, boardId: number) => {
    event.preventDefault();
    const trimmed = renameInput.trim();
    if (!trimmed) {
      return;
    }

    try {
      await onRename(boardId, trimmed);
      setRenamingId(null);
      setError(null);
    } catch (renameError) {
      setError(
        renameError instanceof Error && renameError.message
          ? renameError.message
          : "Could not rename board. Please try again."
      );
    }
  };

  const handleArchiveToggle = async (board: BoardSummary) => {
    try {
      await onArchiveToggle(board.id, !board.is_archived);
      setError(null);
    } catch (archiveError) {
      setError(
        archiveError instanceof Error && archiveError.message
          ? archiveError.message
          : "Could not update board. Please try again."
      );
    }
  };

  const confirmDelete = async (boardId: number) => {
    try {
      await onDelete(boardId);
      setPendingDeleteId(null);
      setError(null);
    } catch (deleteError) {
      setError(
        deleteError instanceof Error && deleteError.message
          ? deleteError.message
          : "Could not delete board. Please try again."
      );
    }
  };

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = newBoardName.trim();
    if (!trimmed) {
      return;
    }

    try {
      await onCreate(trimmed);
      setNewBoardName("");
      setError(null);
    } catch (createError) {
      setError(
        createError instanceof Error && createError.message
          ? createError.message
          : "Could not create board. Please try again."
      );
    }
  };

  return (
    <div className="fixed left-6 top-6 z-20" data-testid="board-switcher">
      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        className="flex items-center gap-2 rounded-full border border-[var(--stroke)] bg-white px-4 py-2 text-sm font-semibold text-[var(--navy-dark)] shadow-sm hover:bg-[var(--surface)]"
      >
        {activeBoard?.name ?? "Boards"}
        <span aria-hidden="true">{isOpen ? "▴" : "▾"}</span>
      </button>

      {isOpen ? (
        <div className="mt-2 w-80 rounded-2xl border border-[var(--stroke)] bg-white p-3 shadow-[var(--shadow)]">
          <ul className="max-h-64 space-y-1 overflow-y-auto">
            {boards.map((board) => (
              <li
                key={board.id}
                className={`rounded-xl px-2 py-2 ${board.id === activeBoardId ? "bg-[var(--surface)]" : ""}`}
              >
                {renamingId === board.id ? (
                  <form
                    onSubmit={(event) => submitRename(event, board.id)}
                    className="flex items-center gap-2"
                  >
                    <input
                      autoFocus
                      aria-label="Rename board"
                      value={renameInput}
                      onChange={(event) => setRenameInput(event.target.value)}
                      className="min-w-0 flex-1 rounded-lg border border-[var(--stroke)] px-2 py-1 text-sm text-[var(--navy-dark)] focus:border-[var(--primary-blue)] focus:outline-none"
                    />
                    <button
                      type="submit"
                      className="rounded-lg bg-[var(--secondary-purple)] px-2 py-1 text-xs font-semibold text-white"
                    >
                      Save
                    </button>
                    <button
                      type="button"
                      onClick={() => setRenamingId(null)}
                      className="text-xs font-medium text-[var(--gray-text)] hover:underline"
                    >
                      Cancel
                    </button>
                  </form>
                ) : (
                  <div className="flex items-center justify-between gap-2">
                    <button
                      type="button"
                      onClick={() => handleSelect(board.id)}
                      className="min-w-0 flex-1 truncate text-left text-sm font-medium text-[var(--navy-dark)]"
                    >
                      {board.name}
                      {board.is_archived ? (
                        <span className="ml-2 rounded-full bg-[var(--surface)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--gray-text)]">
                          Archived
                        </span>
                      ) : null}
                    </button>

                    <div className="flex shrink-0 items-center gap-1 text-xs">
                      <button
                        type="button"
                        onClick={() => startRename(board)}
                        className="rounded-lg px-1.5 py-1 font-medium text-[var(--primary-blue)] hover:underline"
                      >
                        Rename
                      </button>
                      <button
                        type="button"
                        onClick={() => handleArchiveToggle(board)}
                        className="rounded-lg px-1.5 py-1 font-medium text-[var(--primary-blue)] hover:underline"
                      >
                        {board.is_archived ? "Unarchive" : "Archive"}
                      </button>
                      {pendingDeleteId === board.id ? (
                        <>
                          <button
                            type="button"
                            onClick={() => confirmDelete(board.id)}
                            className="rounded-lg px-1.5 py-1 font-semibold text-[var(--secondary-purple)] hover:underline"
                          >
                            Confirm?
                          </button>
                          <button
                            type="button"
                            onClick={() => setPendingDeleteId(null)}
                            className="rounded-lg px-1.5 py-1 font-medium text-[var(--gray-text)] hover:underline"
                          >
                            No
                          </button>
                        </>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setPendingDeleteId(board.id)}
                          className="rounded-lg px-1.5 py-1 font-medium text-[var(--secondary-purple)] hover:underline"
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </li>
            ))}
          </ul>

          {error ? (
            <p role="alert" className="mt-2 text-xs font-medium text-[var(--secondary-purple)]">
              {error}
            </p>
          ) : null}

          <form onSubmit={handleCreate} className="mt-3 flex items-center gap-2 border-t border-[var(--stroke)] pt-3">
            <input
              value={newBoardName}
              onChange={(event) => setNewBoardName(event.target.value)}
              placeholder="New board name"
              className="min-w-0 flex-1 rounded-lg border border-[var(--stroke)] px-2 py-1.5 text-sm text-[var(--navy-dark)] focus:border-[var(--primary-blue)] focus:outline-none"
            />
            <button
              type="submit"
              className="rounded-lg bg-[var(--secondary-purple)] px-3 py-1.5 text-xs font-semibold text-white hover:opacity-90"
            >
              Create
            </button>
          </form>
        </div>
      ) : null}
    </div>
  );
};
