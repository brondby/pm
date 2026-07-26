import type { BoardData } from "@/lib/kanban";

const isBoardData = (value: unknown): value is BoardData => {
    if (!value || typeof value !== "object") {
        return false;
    }

    const candidate = value as { columns?: unknown; cards?: unknown };
    return Array.isArray(candidate.columns) && typeof candidate.cards === "object" && candidate.cards !== null;
};

const getErrorDetail = async (response: Response) => {
    try {
        const payload = (await response.json()) as { detail?: string };
        if (typeof payload.detail === "string" && payload.detail.trim()) {
            return payload.detail;
        }
    } catch {
        // Ignore JSON parsing failures and fall back to status text.
    }

    return response.statusText || `HTTP ${response.status}`;
};

export const getBoard = async (
    username: string,
    options?: { signal?: AbortSignal }
): Promise<BoardData> => {
    const response = await fetch(`/api/board/${encodeURIComponent(username)}`, {
        method: "GET",
        headers: {
            Accept: "application/json",
        },
        signal: options?.signal,
    });

    if (!response.ok) {
        throw new Error(await getErrorDetail(response));
    }

    return (await response.json()) as BoardData;
};

export const putBoard = async (
    username: string,
    board: BoardData,
    options?: { signal?: AbortSignal }
): Promise<BoardData> => {
    const response = await fetch(`/api/board/${encodeURIComponent(username)}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
        },
        body: JSON.stringify(board),
        signal: options?.signal,
    });

    if (!response.ok) {
        throw new Error(await getErrorDetail(response));
    }

    return (await response.json()) as BoardData;
};

export type ChatBoardResponse = {
    reply: string;
    board: BoardData;
};

export const chatBoard = async (
    username: string,
    message: string,
    options?: { signal?: AbortSignal }
): Promise<ChatBoardResponse> => {
    const response = await fetch(`/api/board/${encodeURIComponent(username)}/chat`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
        },
        body: JSON.stringify({ message }),
        signal: options?.signal,
    });

    if (!response.ok) {
        throw new Error(await getErrorDetail(response));
    }

    const payload = (await response.json()) as {
        reply?: unknown;
        board?: unknown;
    };

    if (typeof payload.reply !== "string" || !isBoardData(payload.board)) {
        throw new Error("Malformed chat response from server.");
    }

    return {
        reply: payload.reply,
        board: payload.board,
    };
};
