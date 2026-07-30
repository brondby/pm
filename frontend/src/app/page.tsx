"use client";

import { FormEvent, useEffect, useState } from "react";
import { BoardWorkspace } from "@/components/BoardWorkspace";
import { getCurrentUser, login, logout, signup } from "@/lib/authApi";

type Mode = "login" | "signup";

export default function Home() {
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const [username, setUsername] = useState<string | null>(null);

  const [mode, setMode] = useState<Mode>("login");
  const [usernameInput, setUsernameInput] = useState("");
  const [passwordInput, setPasswordInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let isMounted = true;

    void getCurrentUser().then((user) => {
      if (!isMounted) {
        return;
      }
      setUsername(user?.username ?? null);
      setIsCheckingSession(false);
    });

    return () => {
      isMounted = false;
    };
  }, []);

  const resetForm = () => {
    setUsernameInput("");
    setPasswordInput("");
    setError(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isSubmitting) {
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      const user = mode === "login"
        ? await login(usernameInput, passwordInput)
        : await signup(usernameInput, passwordInput);

      setUsername(user.username);
      resetForm();
    } catch (submitError) {
      setError(
        submitError instanceof Error && submitError.message
          ? submitError.message
          : "Something went wrong. Please try again."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    setUsername(null);
    resetForm();
  };

  const switchMode = (nextMode: Mode) => {
    setMode(nextMode);
    resetForm();
  };

  if (isCheckingSession) {
    return (
      <main className="mx-auto flex min-h-screen w-full max-w-md items-center justify-center px-6">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
          Loading...
        </p>
      </main>
    );
  }

  if (username) {
    return (
      <>
        <div className="fixed right-6 top-6 z-20 flex items-center gap-3">
          <span className="rounded-full border border-[var(--stroke)] bg-white px-4 py-2 text-sm font-medium text-[var(--gray-text)] shadow-sm">
            {username}
          </span>
          <button
            type="button"
            onClick={handleLogout}
            className="rounded-full border border-[var(--stroke)] bg-white px-4 py-2 text-sm font-semibold text-[var(--navy-dark)] shadow-sm hover:bg-[var(--surface)]"
          >
            Logout
          </button>
        </div>
        <BoardWorkspace />
      </>
    );
  }

  const isSignup = mode === "signup";

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-md items-center px-6">
      <section className="w-full rounded-3xl border border-[var(--stroke)] bg-white p-8 shadow-[var(--shadow)]">
        <h1 className="text-3xl font-semibold text-[var(--navy-dark)]">
          {isSignup ? "Create account" : "Sign in"}
        </h1>
        <p className="mt-2 text-sm text-[var(--gray-text)]">
          {isSignup
            ? "Choose a username and password to get started."
            : "Sign in with your account to continue."}
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
              value={usernameInput}
              onChange={(event) => {
                setUsernameInput(event.target.value);
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
              autoComplete={isSignup ? "new-password" : "current-password"}
              value={passwordInput}
              onChange={(event) => {
                setPasswordInput(event.target.value);
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
            disabled={isSubmitting}
            className="w-full rounded-xl bg-[var(--secondary-purple)] px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {isSubmitting ? "Please wait..." : isSignup ? "Create account" : "Login"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-[var(--gray-text)]">
          {isSignup ? "Already have an account?" : "Need an account?"}{" "}
          <button
            type="button"
            onClick={() => switchMode(isSignup ? "login" : "signup")}
            className="font-semibold text-[var(--primary-blue)] hover:underline"
          >
            {isSignup ? "Sign in" : "Create one"}
          </button>
        </p>
      </section>
    </main>
  );
}
