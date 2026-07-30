import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { KanbanBoard } from "@/components/KanbanBoard";
import { chatBoard, getBoard, putBoard } from "@/lib/boardApi";
import type { BoardData } from "@/lib/kanban";

vi.mock("@/lib/boardApi", () => ({
  getBoard: vi.fn(),
  putBoard: vi.fn(),
  chatBoard: vi.fn(),
}));

const sampleBoard = (): BoardData => ({
  columns: [
    { id: "col-backlog", title: "Backlog", cardIds: ["card-1"] },
    { id: "col-review", title: "Review", cardIds: [] },
    { id: "col-progress", title: "In Progress", cardIds: [] },
    { id: "col-done", title: "Done", cardIds: [] },
    { id: "col-archive", title: "Archive", cardIds: [] },
  ],
  cards: {
    "card-1": { id: "card-1", title: "Initial task", details: "Seed details" },
  },
});

const cloneBoard = (board: BoardData): BoardData => JSON.parse(JSON.stringify(board));

const mockedGetBoard = vi.mocked(getBoard);
const mockedPutBoard = vi.mocked(putBoard);
const mockedChatBoard = vi.mocked(chatBoard);

describe("KanbanBoard backend persistence", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.sessionStorage.clear();
  });

  it("shows a loading indicator while loading the board", async () => {
    let resolveGet: (value: BoardData) => void = () => { };
    mockedGetBoard.mockReturnValue(
      new Promise<BoardData>((resolve) => {
        resolveGet = resolve;
      })
    );

    render(<KanbanBoard boardId={1} />);

    expect(screen.getByText(/loading board/i)).toBeInTheDocument();

    resolveGet(sampleBoard());

    await screen.findByText(/kanban studio/i);
  });

  it("loads the board and does not save immediately after initial GET", async () => {
    mockedGetBoard.mockResolvedValue(sampleBoard());
    mockedPutBoard.mockResolvedValue(sampleBoard());

    render(<KanbanBoard boardId={1} />);

    await screen.findByText(/kanban studio/i);

    expect(mockedGetBoard).toHaveBeenCalledWith(1, expect.any(Object));
    expect(mockedPutBoard).not.toHaveBeenCalled();
  });

  it("shows a user-friendly error when loading fails", async () => {
    mockedGetBoard.mockRejectedValue(new Error("Network down"));

    render(<KanbanBoard boardId={1} />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Network down");
    expect(screen.queryByText(/kanban studio/i)).not.toBeInTheDocument();
  });

  it("saves after a board change", async () => {
    const board = sampleBoard();
    mockedGetBoard.mockResolvedValue(board);
    mockedPutBoard.mockImplementation(async (_boardId, payload) => payload);

    render(<KanbanBoard boardId={1} />);

    const heading = await screen.findByText(/kanban studio/i);
    expect(heading).toBeInTheDocument();

    const firstColumn = screen.getByTestId("column-col-backlog");
    const addButton = within(firstColumn).getByRole("button", { name: /add a card/i });
    await userEvent.click(addButton);
    await userEvent.type(within(firstColumn).getByPlaceholderText(/card title/i), "New card");
    await userEvent.type(within(firstColumn).getByPlaceholderText(/details/i), "Notes");
    await userEvent.click(within(firstColumn).getByRole("button", { name: /add card/i }));

    await waitFor(() => expect(mockedPutBoard).toHaveBeenCalledTimes(1));
    expect(mockedPutBoard.mock.calls[0]?.[0]).toBe(1);
  });

  it("keeps current board state and shows error when save fails", async () => {
    mockedGetBoard.mockResolvedValue(sampleBoard());
    mockedPutBoard.mockRejectedValue(new Error("Save failed"));

    render(<KanbanBoard boardId={1} />);

    await screen.findByText(/kanban studio/i);

    const firstColumn = screen.getByTestId("column-col-backlog");
    await userEvent.click(within(firstColumn).getByRole("button", { name: /add a card/i }));
    await userEvent.type(within(firstColumn).getByPlaceholderText(/card title/i), "Unsaved card");
    await userEvent.click(within(firstColumn).getByRole("button", { name: /add card/i }));

    expect(await within(firstColumn).findByText("Unsaved card")).toBeInTheDocument();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/could not save your latest change/i);
  });

  it("saves the latest board after rapid consecutive changes without losing newer state", async () => {
    const board = sampleBoard();
    mockedGetBoard.mockResolvedValue(board);

    let resolveFirstSave: () => void = () => { };
    const savedPayloads: BoardData[] = [];

    mockedPutBoard.mockImplementation((_boardId, payload) => {
      const snapshot = cloneBoard(payload);
      savedPayloads.push(snapshot);

      if (savedPayloads.length === 1) {
        return new Promise<BoardData>((resolve) => {
          resolveFirstSave = () => resolve(snapshot);
        });
      }

      return Promise.resolve(snapshot);
    });

    render(<KanbanBoard boardId={1} />);

    await screen.findByText(/kanban studio/i);

    const column = screen.getByTestId("column-col-backlog");

    await userEvent.click(within(column).getByRole("button", { name: /add a card/i }));
    await userEvent.type(within(column).getByPlaceholderText(/card title/i), "Card A");
    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    await userEvent.click(within(column).getByRole("button", { name: /add a card/i }));
    await userEvent.type(within(column).getByPlaceholderText(/card title/i), "Card B");
    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    await waitFor(() => expect(savedPayloads.length).toBe(1));

    resolveFirstSave();

    await waitFor(() => expect(savedPayloads.length).toBe(2));

    const latestCards = Object.values(savedPayloads[1].cards).map((card) => card.title);
    expect(latestCards).toContain("Card A");
    expect(latestCards).toContain("Card B");
  });

  it("sends chat command, applies returned board, and does not trigger duplicate PUT", async () => {
    const board = sampleBoard();
    mockedGetBoard.mockResolvedValue(board);

    const chatBoardState = cloneBoard(board);
    chatBoardState.columns[0].cardIds = [];
    chatBoardState.columns[3].cardIds = ["card-1"];
    mockedChatBoard.mockResolvedValue({
      reply: 'Moved "Initial task" to "Done".',
      board: chatBoardState,
    });

    render(<KanbanBoard boardId={1} />);

    await screen.findByText(/kanban studio/i);

    await userEvent.type(screen.getByLabelText(/command/i), "move card Initial task to Done");
    await userEvent.click(screen.getByRole("button", { name: /^send$/i }));

    await screen.findByText('Moved "Initial task" to "Done".');

    expect(mockedChatBoard).toHaveBeenCalledWith(
      1,
      "move card Initial task to Done",
      expect.any(Object)
    );
    expect(mockedPutBoard).not.toHaveBeenCalled();

    const doneColumn = screen.getByTestId("column-col-done");
    expect(within(doneColumn).getByText("Initial task")).toBeInTheDocument();
  });

  it("keeps board interactions usable while chat request is pending", async () => {
    mockedGetBoard.mockResolvedValue(sampleBoard());
    mockedPutBoard.mockImplementation(async (_boardId, payload) => payload);

    let resolveChat: () => void = () => { };
    mockedChatBoard.mockReturnValue(
      new Promise((resolve) => {
        resolveChat = () =>
          resolve({
            reply: "ok",
            board: sampleBoard(),
          });
      })
    );

    render(<KanbanBoard boardId={1} />);

    await screen.findByText(/kanban studio/i);

    await userEvent.type(screen.getByLabelText(/command/i), "rename column backlog to ideas");
    await userEvent.click(screen.getByRole("button", { name: /^send$/i }));

    expect(screen.getByRole("button", { name: /sending/i })).toBeDisabled();

    const firstColumn = screen.getByTestId("column-col-backlog");
    await userEvent.click(within(firstColumn).getByRole("button", { name: /add a card/i }));
    await userEvent.type(within(firstColumn).getByPlaceholderText(/card title/i), "Still works");
    await userEvent.click(within(firstColumn).getByRole("button", { name: /add card/i }));

    expect(await within(firstColumn).findByText("Still works")).toBeInTheDocument();

    resolveChat();
    await screen.findByText("ok");
  });

  it("shows backend chat error message when AI request fails", async () => {
    mockedGetBoard.mockResolvedValue(sampleBoard());
    mockedChatBoard.mockRejectedValue(new Error("AI request timed out. Please try again."));

    render(<KanbanBoard boardId={1} />);

    await screen.findByText(/kanban studio/i);

    await userEvent.type(screen.getByLabelText(/command/i), "move card Initial task to Done");
    await userEvent.click(screen.getByRole("button", { name: /^send$/i }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("AI request timed out. Please try again.");
    await waitFor(() =>
      expect(screen.getAllByText("AI request timed out. Please try again.").length).toBeGreaterThan(0)
    );
  });

  it("shows malformed response message when chat response validation fails", async () => {
    mockedGetBoard.mockResolvedValue(sampleBoard());
    mockedChatBoard.mockRejectedValue(new Error("Malformed chat response from server."));

    render(<KanbanBoard boardId={1} />);

    await screen.findByText(/kanban studio/i);

    await userEvent.type(screen.getByLabelText(/command/i), "move card Initial task to Done");
    await userEvent.click(screen.getByRole("button", { name: /^send$/i }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Malformed chat response from server.");
    await waitFor(() =>
      expect(screen.getAllByText("Malformed chat response from server.").length).toBeGreaterThan(0)
    );
  });

  it("preserves chat history for current browser session", async () => {
    mockedGetBoard.mockResolvedValue(sampleBoard());
    mockedChatBoard.mockResolvedValue({
      reply: "Assistant reply",
      board: sampleBoard(),
    });

    const { unmount } = render(<KanbanBoard boardId={1} />);
    await screen.findByText(/kanban studio/i);

    await userEvent.type(screen.getByLabelText(/command/i), "delete card Initial task");
    await userEvent.click(screen.getByRole("button", { name: /^send$/i }));

    await screen.findByText("Assistant reply");
    unmount();

    mockedGetBoard.mockResolvedValue(sampleBoard());
    render(<KanbanBoard boardId={1} />);

    await screen.findByText(/kanban studio/i);
    expect(screen.getByText("delete card Initial task")).toBeInTheDocument();
    expect(screen.getByText("Assistant reply")).toBeInTheDocument();
  });
});