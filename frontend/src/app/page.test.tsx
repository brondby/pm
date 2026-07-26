import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import Home from "@/app/page";

vi.mock("@/components/KanbanBoard", () => ({
    KanbanBoard: ({ username }: { username: string }) => (
        <div data-testid="kanban-board">Board for {username}</div>
    ),
}));

describe("Home auth flow", () => {
    it("shows the login form on initial load", () => {
        render(<Home />);

        expect(screen.getByRole("heading", { name: /sign in/i })).toBeInTheDocument();
        expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    });

    it("shows a friendly error for invalid credentials", async () => {
        render(<Home />);

        await userEvent.type(screen.getByLabelText(/username/i), "wrong");
        await userEvent.type(screen.getByLabelText(/password/i), "credentials");
        await userEvent.click(screen.getByRole("button", { name: /login/i }));

        expect(screen.getByRole("alert")).toHaveTextContent(
            "Invalid credentials. Please try again."
        );
        expect(screen.getByRole("heading", { name: /sign in/i })).toBeInTheDocument();
    });

    it("shows the board after valid login", async () => {
        render(<Home />);

        await userEvent.type(screen.getByLabelText(/username/i), "user");
        await userEvent.type(screen.getByLabelText(/password/i), "password");
        await userEvent.click(screen.getByRole("button", { name: /login/i }));

        expect(screen.getByTestId("kanban-board")).toHaveTextContent("Board for user");
        expect(screen.getByRole("button", { name: /logout/i })).toBeInTheDocument();
    });

    it("returns to login screen after logout", async () => {
        render(<Home />);

        await userEvent.type(screen.getByLabelText(/username/i), "user");
        await userEvent.type(screen.getByLabelText(/password/i), "password");
        await userEvent.click(screen.getByRole("button", { name: /login/i }));

        await userEvent.click(screen.getByRole("button", { name: /logout/i }));

        expect(screen.getByRole("heading", { name: /sign in/i })).toBeInTheDocument();
        expect(screen.queryByTestId("kanban-board")).not.toBeInTheDocument();
    });
});