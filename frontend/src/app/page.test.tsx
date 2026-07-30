import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Home from "@/app/page";

vi.mock("@/components/BoardWorkspace", () => ({
    BoardWorkspace: () => <div data-testid="board-workspace">Board workspace</div>,
}));

type MockResponseInit = {
    status: number;
    body: unknown;
};

const jsonResponse = ({ status, body }: MockResponseInit): Response =>
    new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
    });

const mockFetch = (handlers: Record<string, () => MockResponseInit>) => {
    vi.stubGlobal(
        "fetch",
        vi.fn(async (input: RequestInfo | URL) => {
            const url = typeof input === "string" ? input : input.toString();
            const handler = Object.entries(handlers).find(([path]) => url.includes(path));
            if (!handler) {
                throw new Error(`Unhandled fetch in test: ${url}`);
            }
            return jsonResponse(handler[1]());
        })
    );
};

describe("Home auth flow", () => {
    beforeEach(() => {
        window.sessionStorage.clear();
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it("shows the login form when there is no active session", async () => {
        mockFetch({ "/api/auth/me": () => ({ status: 401, body: { detail: "Not authenticated." } }) });

        render(<Home />);

        expect(await screen.findByRole("heading", { name: /sign in/i })).toBeInTheDocument();
        expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    });

    it("skips the login form when a session is already active", async () => {
        mockFetch({ "/api/auth/me": () => ({ status: 200, body: { username: "user" } }) });

        render(<Home />);

        expect(await screen.findByTestId("board-workspace")).toHaveTextContent("Board workspace");
    });

    it("shows a friendly error for invalid credentials without leaking backend detail", async () => {
        mockFetch({
            "/api/auth/me": () => ({ status: 401, body: { detail: "Not authenticated." } }),
            "/api/auth/login": () => ({ status: 401, body: { detail: "Invalid username or password." } }),
        });

        render(<Home />);
        await screen.findByRole("heading", { name: /sign in/i });

        await userEvent.type(screen.getByLabelText(/username/i), "wrong");
        await userEvent.type(screen.getByLabelText(/password/i), "credentials");
        await userEvent.click(screen.getByRole("button", { name: /login/i }));

        expect(await screen.findByRole("alert")).toHaveTextContent(
            "Invalid username or password."
        );
        expect(screen.getByRole("heading", { name: /sign in/i })).toBeInTheDocument();
    });

    it("shows the board after valid login", async () => {
        mockFetch({
            "/api/auth/me": () => ({ status: 401, body: { detail: "Not authenticated." } }),
            "/api/auth/login": () => ({ status: 200, body: { username: "user" } }),
        });

        render(<Home />);
        await screen.findByRole("heading", { name: /sign in/i });

        await userEvent.type(screen.getByLabelText(/username/i), "user");
        await userEvent.type(screen.getByLabelText(/password/i), "password");
        await userEvent.click(screen.getByRole("button", { name: /login/i }));

        expect(await screen.findByTestId("board-workspace")).toHaveTextContent("Board workspace");
        expect(screen.getByText("user")).toBeInTheDocument();
        expect(screen.getByRole("button", { name: /logout/i })).toBeInTheDocument();
    });

    it("returns to login screen after logout", async () => {
        mockFetch({
            "/api/auth/me": () => ({ status: 401, body: { detail: "Not authenticated." } }),
            "/api/auth/login": () => ({ status: 200, body: { username: "user" } }),
            "/api/auth/logout": () => ({ status: 200, body: { ok: true } }),
        });

        render(<Home />);
        await screen.findByRole("heading", { name: /sign in/i });

        await userEvent.type(screen.getByLabelText(/username/i), "user");
        await userEvent.type(screen.getByLabelText(/password/i), "password");
        await userEvent.click(screen.getByRole("button", { name: /login/i }));
        await screen.findByTestId("board-workspace");

        await userEvent.click(screen.getByRole("button", { name: /logout/i }));

        expect(await screen.findByRole("heading", { name: /sign in/i })).toBeInTheDocument();
        expect(screen.queryByTestId("board-workspace")).not.toBeInTheDocument();
    });

    it("supports creating a new account via the signup toggle", async () => {
        mockFetch({
            "/api/auth/me": () => ({ status: 401, body: { detail: "Not authenticated." } }),
            "/api/auth/signup": () => ({ status: 200, body: { username: "newperson" } }),
        });

        render(<Home />);
        await screen.findByRole("heading", { name: /sign in/i });

        await userEvent.click(screen.getByRole("button", { name: /create one/i }));
        expect(screen.getByRole("heading", { name: /create account/i })).toBeInTheDocument();

        await userEvent.type(screen.getByLabelText(/username/i), "newperson");
        await userEvent.type(screen.getByLabelText(/password/i), "s3cret-pass");
        await userEvent.click(screen.getByRole("button", { name: /create account/i }));

        expect(await screen.findByTestId("board-workspace")).toHaveTextContent("Board workspace");
    });

    it("shows a friendly error for a duplicate username on signup", async () => {
        mockFetch({
            "/api/auth/me": () => ({ status: 401, body: { detail: "Not authenticated." } }),
            "/api/auth/signup": () => ({ status: 409, body: { detail: "Username is already taken." } }),
        });

        render(<Home />);
        await screen.findByRole("heading", { name: /sign in/i });
        await userEvent.click(screen.getByRole("button", { name: /create one/i }));

        await userEvent.type(screen.getByLabelText(/username/i), "user");
        await userEvent.type(screen.getByLabelText(/password/i), "s3cret-pass");
        await userEvent.click(screen.getByRole("button", { name: /create account/i }));

        expect(await screen.findByRole("alert")).toHaveTextContent("Username is already taken.");
    });

    it("shows a generic message on network failure instead of a raw exception", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn(async (input: RequestInfo | URL) => {
                const url = typeof input === "string" ? input : input.toString();
                if (url.includes("/api/auth/me")) {
                    return jsonResponse({ status: 401, body: { detail: "Not authenticated." } });
                }
                throw new TypeError("Failed to fetch");
            })
        );

        render(<Home />);
        await screen.findByRole("heading", { name: /sign in/i });

        await userEvent.type(screen.getByLabelText(/username/i), "user");
        await userEvent.type(screen.getByLabelText(/password/i), "password");
        await userEvent.click(screen.getByRole("button", { name: /login/i }));

        const alert = await screen.findByRole("alert");
        expect(alert).not.toHaveTextContent("TypeError");
        expect(alert).not.toHaveTextContent("Failed to fetch");
        await waitFor(() =>
            expect(alert).toHaveTextContent("Could not reach the server. Please check your connection and try again.")
        );
    });
});
