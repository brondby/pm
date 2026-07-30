import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BoardWorkspace } from "@/components/BoardWorkspace";
import {
  createBoard,
  deleteBoard,
  listBoards,
  renameBoard,
  setBoardArchived,
  type BoardSummary,
} from "@/lib/boardsApi";

vi.mock("@/lib/boardsApi", () => ({
  listBoards: vi.fn(),
  createBoard: vi.fn(),
  renameBoard: vi.fn(),
  setBoardArchived: vi.fn(),
  deleteBoard: vi.fn(),
}));

vi.mock("@/components/KanbanBoard", () => ({
  KanbanBoard: ({ boardId }: { boardId: number }) => (
    <div data-testid="kanban-board">Board {boardId}</div>
  ),
}));

const board = (overrides: Partial<BoardSummary> = {}): BoardSummary => ({
  id: 1,
  name: "My Board",
  is_archived: false,
  created_at: "2026-01-01T00:00:00.000Z",
  updated_at: "2026-01-01T00:00:00.000Z",
  ...overrides,
});

const mockedListBoards = vi.mocked(listBoards);
const mockedCreateBoard = vi.mocked(createBoard);
const mockedDeleteBoard = vi.mocked(deleteBoard);
const mockedSetBoardArchived = vi.mocked(setBoardArchived);
const mockedRenameBoard = vi.mocked(renameBoard);

describe("BoardWorkspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedRenameBoard.mockResolvedValue(board());
  });

  it("renders the default board once boards load", async () => {
    mockedListBoards.mockResolvedValue([board()]);

    render(<BoardWorkspace />);

    expect(await screen.findByTestId("kanban-board")).toHaveTextContent("Board 1");
    expect(screen.getByTestId("board-switcher")).toBeInTheDocument();
  });

  it("defaults to the most recently updated non-archived board, never an archived one", async () => {
    mockedListBoards.mockResolvedValue([
      board({ id: 1, name: "Archived Board", is_archived: true }),
      board({ id: 2, name: "Active Board", is_archived: false }),
    ]);

    render(<BoardWorkspace />);

    expect(await screen.findByTestId("kanban-board")).toHaveTextContent("Board 2");
  });

  it("shows a first-class empty state with zero boards, without auto-creating one", async () => {
    mockedListBoards.mockResolvedValue([]);

    render(<BoardWorkspace />);

    expect(await screen.findByText(/don't have any boards yet/i)).toBeInTheDocument();
    expect(screen.queryByTestId("kanban-board")).not.toBeInTheDocument();
    expect(mockedCreateBoard).not.toHaveBeenCalled();
  });

  it("creating a board from the empty state switches to it", async () => {
    mockedListBoards.mockResolvedValueOnce([]);
    mockedCreateBoard.mockResolvedValue(board({ id: 5, name: "New Board" }));
    mockedListBoards.mockResolvedValueOnce([board({ id: 5, name: "New Board" })]);

    render(<BoardWorkspace />);

    await screen.findByText(/don't have any boards yet/i);

    await userEvent.type(screen.getByLabelText(/board name/i), "New Board");
    await userEvent.click(screen.getByRole("button", { name: /create board/i }));

    expect(await screen.findByTestId("kanban-board")).toHaveTextContent("Board 5");
  });

  it("shows an all-archived state and never treats an archived board as active", async () => {
    mockedListBoards.mockResolvedValue([board({ is_archived: true })]);

    render(<BoardWorkspace />);

    expect(await screen.findByText(/all your boards are archived/i)).toBeInTheDocument();
    expect(screen.queryByTestId("kanban-board")).not.toBeInTheDocument();
  });

  it("unarchiving a board from the all-archived state makes it active", async () => {
    mockedListBoards.mockResolvedValueOnce([board({ is_archived: true })]);
    mockedSetBoardArchived.mockResolvedValue(board({ is_archived: false }));
    mockedListBoards.mockResolvedValueOnce([board({ is_archived: false })]);

    render(<BoardWorkspace />);

    await screen.findByText(/all your boards are archived/i);
    await userEvent.click(screen.getByRole("button", { name: /unarchive/i }));

    expect(await screen.findByTestId("kanban-board")).toHaveTextContent("Board 1");
  });

  it("deleting the only board returns to the empty state without auto-creating a replacement", async () => {
    mockedListBoards.mockResolvedValueOnce([board()]);
    mockedDeleteBoard.mockResolvedValue(undefined);
    mockedListBoards.mockResolvedValueOnce([]);

    render(<BoardWorkspace />);
    await screen.findByTestId("kanban-board");

    await userEvent.click(screen.getByRole("button", { name: /my board/i }));
    await userEvent.click(screen.getByRole("button", { name: /^delete$/i }));
    await userEvent.click(screen.getByRole("button", { name: /confirm\?/i }));

    expect(await screen.findByText(/don't have any boards yet/i)).toBeInTheDocument();
    expect(mockedCreateBoard).not.toHaveBeenCalled();
  });

  it("shows a friendly error when the board list fails to load", async () => {
    mockedListBoards.mockRejectedValue(new Error("Could not load your boards. Please try again."));

    render(<BoardWorkspace />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not load your boards. Please try again."
    );
  });
});
