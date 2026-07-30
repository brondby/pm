export type AuthUser = {
    username: string;
};

const NETWORK_ERROR_MESSAGE = "Could not reach the server. Please check your connection and try again.";

const getErrorMessage = async (response: Response, fallback: string): Promise<string> => {
    try {
        const payload = (await response.json()) as { detail?: string };
        if (typeof payload.detail === "string" && payload.detail.trim()) {
            return payload.detail;
        }
    } catch {
        // Ignore JSON parsing failures and fall back to a friendly message below.
    }

    return fallback;
};

const postAuth = async (
    path: string,
    body: Record<string, string>,
    fallbackError: string
): Promise<AuthUser> => {
    let response: Response;
    try {
        response = await fetch(path, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Accept: "application/json",
            },
            body: JSON.stringify(body),
        });
    } catch {
        throw new Error(NETWORK_ERROR_MESSAGE);
    }

    if (!response.ok) {
        throw new Error(await getErrorMessage(response, fallbackError));
    }

    return (await response.json()) as AuthUser;
};

export const signup = (username: string, password: string): Promise<AuthUser> =>
    postAuth(
        "/api/auth/signup",
        { username, password },
        "Could not create your account. Please try again."
    );

export const login = (username: string, password: string): Promise<AuthUser> =>
    postAuth("/api/auth/login", { username, password }, "Invalid username or password.");

export const logout = async (): Promise<void> => {
    try {
        await fetch("/api/auth/logout", { method: "POST" });
    } catch {
        // Logout is best-effort from the client's perspective; the session cookie
        // is cleared client-side by the browser regardless of network failures here.
    }
};

export const getCurrentUser = async (): Promise<AuthUser | null> => {
    let response: Response;
    try {
        response = await fetch("/api/auth/me", { headers: { Accept: "application/json" } });
    } catch {
        return null;
    }

    if (!response.ok) {
        return null;
    }

    return (await response.json()) as AuthUser;
};
