export type BoardSummary = {
    id: number;
    name: string;
    is_archived: boolean;
    created_at: string;
    updated_at: string;
};

const isBoardSummary = (value: unknown): value is BoardSummary => {
    if (!value || typeof value !== "object") {
        return false;
    }

    const candidate = value as Record<string, unknown>;
    return (
        typeof candidate.id === "number" &&
        typeof candidate.name === "string" &&
        typeof candidate.is_archived === "boolean"
    );
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

export const listBoards = async (options?: { signal?: AbortSignal }): Promise<BoardSummary[]> => {
    const response = await fetch("/api/boards", {
        method: "GET",
        headers: { Accept: "application/json" },
        signal: options?.signal,
    });

    if (!response.ok) {
        throw new Error(await getErrorDetail(response));
    }

    const payload = (await response.json()) as unknown;
    if (!Array.isArray(payload) || !payload.every(isBoardSummary)) {
        throw new Error("Malformed board list response from server.");
    }

    return payload;
};

export const createBoard = async (name: string): Promise<BoardSummary> => {
    const response = await fetch("/api/boards", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
        },
        body: JSON.stringify({ name }),
    });

    if (!response.ok) {
        throw new Error(await getErrorDetail(response));
    }

    const payload = (await response.json()) as unknown;
    if (!isBoardSummary(payload)) {
        throw new Error("Malformed board response from server.");
    }

    return payload;
};

export const renameBoard = async (boardId: number, name: string): Promise<BoardSummary> => {
    const response = await fetch(`/api/boards/${boardId}`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
        },
        body: JSON.stringify({ name }),
    });

    if (!response.ok) {
        throw new Error(await getErrorDetail(response));
    }

    const payload = (await response.json()) as unknown;
    if (!isBoardSummary(payload)) {
        throw new Error("Malformed board response from server.");
    }

    return payload;
};

export const setBoardArchived = async (
    boardId: number,
    isArchived: boolean
): Promise<BoardSummary> => {
    const response = await fetch(`/api/boards/${boardId}`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
        },
        body: JSON.stringify({ is_archived: isArchived }),
    });

    if (!response.ok) {
        throw new Error(await getErrorDetail(response));
    }

    const payload = (await response.json()) as unknown;
    if (!isBoardSummary(payload)) {
        throw new Error("Malformed board response from server.");
    }

    return payload;
};

export const deleteBoard = async (boardId: number): Promise<void> => {
    const response = await fetch(`/api/boards/${boardId}`, {
        method: "DELETE",
    });

    if (!response.ok) {
        throw new Error(await getErrorDetail(response));
    }
};
