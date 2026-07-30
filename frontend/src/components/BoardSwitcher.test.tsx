import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { BoardSwitcher } from "@/components/BoardSwitcher";
import type { BoardSummary } from "@/lib/boardsApi";

const board = (overrides: Partial<BoardSummary> = {}): BoardSummary => ({
  id: 1,
  name: "My Board",
  is_archived: false,
  created_at: "2026-01-01T00:00:00.000Z",
  updated_at: "2026-01-01T00:00:00.000Z",
  ...overrides,
});

describe("BoardSwitcher", () => {
  it("shows the active board name on the trigger and opens the list on click", async () => {
    render(
      <BoardSwitcher
        boards={[board(), board({ id: 2, name: "Second Board" })]}
        activeBoardId={1}
        onSelect={vi.fn()}
        onCreate={vi.fn()}
        onRename={vi.fn()}
        onArchiveToggle={vi.fn()}
        onDelete={vi.fn()}
      />
    );

    expect(screen.getByRole("button", { name: /my board/i })).toBeInTheDocument();
    expect(screen.queryByText("Second Board")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /my board/i }));

    expect(screen.getByText("Second Board")).toBeInTheDocument();
  });

  it("calls onSelect when picking a different board", async () => {
    const onSelect = vi.fn();
    render(
      <BoardSwitcher
        boards={[board(), board({ id: 2, name: "Second Board" })]}
        activeBoardId={1}
        onSelect={onSelect}
        onCreate={vi.fn()}
        onRename={vi.fn()}
        onArchiveToggle={vi.fn()}
        onDelete={vi.fn()}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: /my board/i }));
    await userEvent.click(screen.getByText("Second Board"));

    expect(onSelect).toHaveBeenCalledWith(2);
  });

  it("shows an archived badge for archived boards", async () => {
    render(
      <BoardSwitcher
        boards={[board({ is_archived: true })]}
        activeBoardId={1}
        onSelect={vi.fn()}
        onCreate={vi.fn()}
        onRename={vi.fn()}
        onArchiveToggle={vi.fn()}
        onDelete={vi.fn()}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: /my board/i }));
    expect(screen.getByText("Archived")).toBeInTheDocument();
  });

  it("renames a board via the inline rename form", async () => {
    const onRename = vi.fn().mockResolvedValue(undefined);
    render(
      <BoardSwitcher
        boards={[board()]}
        activeBoardId={1}
        onSelect={vi.fn()}
        onCreate={vi.fn()}
        onRename={onRename}
        onArchiveToggle={vi.fn()}
        onDelete={vi.fn()}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: /my board/i }));
    await userEvent.click(screen.getByRole("button", { name: /rename/i }));

    const input = screen.getByDisplayValue("My Board");
    await userEvent.clear(input);
    await userEvent.type(input, "Renamed Board");
    await userEvent.click(screen.getByRole("button", { name: /save/i }));

    expect(onRename).toHaveBeenCalledWith(1, "Renamed Board");
  });

  it("toggles archive state", async () => {
    const onArchiveToggle = vi.fn().mockResolvedValue(undefined);
    render(
      <BoardSwitcher
        boards={[board()]}
        activeBoardId={1}
        onSelect={vi.fn()}
        onCreate={vi.fn()}
        onRename={vi.fn()}
        onArchiveToggle={onArchiveToggle}
        onDelete={vi.fn()}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: /my board/i }));
    await userEvent.click(screen.getByRole("button", { name: /^archive$/i }));

    expect(onArchiveToggle).toHaveBeenCalledWith(1, true);
  });

  it("requires a confirmation click before deleting a board", async () => {
    const onDelete = vi.fn().mockResolvedValue(undefined);
    render(
      <BoardSwitcher
        boards={[board()]}
        activeBoardId={1}
        onSelect={vi.fn()}
        onCreate={vi.fn()}
        onRename={vi.fn()}
        onArchiveToggle={vi.fn()}
        onDelete={onDelete}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: /my board/i }));
    await userEvent.click(screen.getByRole("button", { name: /^delete$/i }));

    // First click only arms the confirmation - must not delete yet.
    expect(onDelete).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: /confirm\?/i })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /confirm\?/i }));
    expect(onDelete).toHaveBeenCalledWith(1);
  });

  it("cancelling the delete confirmation does not delete", async () => {
    const onDelete = vi.fn();
    render(
      <BoardSwitcher
        boards={[board()]}
        activeBoardId={1}
        onSelect={vi.fn()}
        onCreate={vi.fn()}
        onRename={vi.fn()}
        onArchiveToggle={vi.fn()}
        onDelete={onDelete}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: /my board/i }));
    await userEvent.click(screen.getByRole("button", { name: /^delete$/i }));
    await userEvent.click(screen.getByRole("button", { name: /^no$/i }));

    expect(onDelete).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: /confirm\?/i })).not.toBeInTheDocument();
  });

  it("creates a board via the inline create form", async () => {
    const onCreate = vi.fn().mockResolvedValue(undefined);
    render(
      <BoardSwitcher
        boards={[board()]}
        activeBoardId={1}
        onSelect={vi.fn()}
        onCreate={onCreate}
        onRename={vi.fn()}
        onArchiveToggle={vi.fn()}
        onDelete={vi.fn()}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: /my board/i }));
    await userEvent.type(screen.getByPlaceholderText(/new board name/i), "Marketing");
    await userEvent.click(screen.getByRole("button", { name: /^create$/i }));

    expect(onCreate).toHaveBeenCalledWith("Marketing");
  });

  it("shows a friendly error if a mutation fails", async () => {
    const onDelete = vi.fn().mockRejectedValue(new Error("Board not found."));
    render(
      <BoardSwitcher
        boards={[board()]}
        activeBoardId={1}
        onSelect={vi.fn()}
        onCreate={vi.fn()}
        onRename={vi.fn()}
        onArchiveToggle={vi.fn()}
        onDelete={onDelete}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: /my board/i }));
    await userEvent.click(screen.getByRole("button", { name: /^delete$/i }));
    await userEvent.click(screen.getByRole("button", { name: /confirm\?/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Board not found.");
  });
});
