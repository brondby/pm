"use client";

import { FormEvent, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";

const VALID_USERNAME = "user";
const VALID_PASSWORD = "password";
const AUTH_STORAGE_KEY = "pm-auth-username";

export default function Home() {
  const initialUsername =
    typeof window === "undefined"
      ? ""
      : window.sessionStorage.getItem(AUTH_STORAGE_KEY) === VALID_USERNAME
        ? VALID_USERNAME
        : "";
  const [username, setUsername] = useState(initialUsername);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(initialUsername === VALID_USERNAME);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (username === VALID_USERNAME && password === VALID_PASSWORD) {
      setIsAuthenticated(true);
      setPassword("");
      setError(null);

      if (typeof window !== "undefined") {
        window.sessionStorage.setItem(AUTH_STORAGE_KEY, username);
      }

      return;
    }

    setError("Invalid credentials. Please try again.");
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setUsername("");
    setPassword("");
    setError(null);

    if (typeof window !== "undefined") {
      window.sessionStorage.removeItem(AUTH_STORAGE_KEY);
    }
  };

  if (isAuthenticated) {
    return (
      <>
        <div className="fixed right-6 top-6 z-20">
          <button
            type="button"
            onClick={handleLogout}
            className="rounded-full border border-[var(--stroke)] bg-white px-4 py-2 text-sm font-semibold text-[var(--navy-dark)] shadow-sm hover:bg-[var(--surface)]"
          >
            Logout
          </button>
        </div>
        <KanbanBoard username={username} />
      </>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-md items-center px-6">
      <section className="w-full rounded-3xl border border-[var(--stroke)] bg-white p-8 shadow-[var(--shadow)]">
        <h1 className="text-3xl font-semibold text-[var(--navy-dark)]">Sign in</h1>
        <p className="mt-2 text-sm text-[var(--gray-text)]">
          Use your MVP credentials to continue.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label
              htmlFor="username"
              className="block text-sm font-medium text-[var(--navy-dark)]"
            >
              Username
            </label>
            <input
              id="username"
              name="username"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(event) => {
                setUsername(event.target.value);
                setError(null);
              }}
              className="mt-1 w-full rounded-xl border border-[var(--stroke)] px-3 py-2 text-sm text-[var(--navy-dark)] focus:border-[var(--primary-blue)] focus:outline-none"
              required
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-[var(--navy-dark)]"
            >
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => {
                setPassword(event.target.value);
                setError(null);
              }}
              className="mt-1 w-full rounded-xl border border-[var(--stroke)] px-3 py-2 text-sm text-[var(--navy-dark)] focus:border-[var(--primary-blue)] focus:outline-none"
              required
            />
          </div>

          {error ? (
            <p role="alert" className="text-sm text-[var(--secondary-purple)]">
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            className="w-full rounded-xl bg-[var(--secondary-purple)] px-4 py-2 text-sm font-semibold text-white hover:opacity-90"
          >
            Login
          </button>
        </form>
      </section>
    </main>
  );
}
