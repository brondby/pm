import { useState, type FormEvent, type SVGProps } from "react";
import type { CardMetadata } from "@/lib/kanban";

const initialFormState = { title: "", details: "" };
const initialMetadataState: CardMetadata = { label: "", dueDate: "", assignee: "" };

const PlusIcon = (props: SVGProps<SVGSVGElement>) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 20 20"
    fill="none"
    stroke="currentColor"
    strokeWidth={1.8}
    strokeLinecap="round"
    aria-hidden="true"
    {...props}
  >
    <path d="M10 4.5v11" />
    <path d="M4.5 10h11" />
  </svg>
);

const XIcon = (props: SVGProps<SVGSVGElement>) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 20 20"
    fill="none"
    stroke="currentColor"
    strokeWidth={1.8}
    strokeLinecap="round"
    aria-hidden="true"
    {...props}
  >
    <path d="M5.5 5.5l9 9" />
    <path d="M14.5 5.5l-9 9" />
  </svg>
);

type NewCardFormProps = {
  onAdd: (title: string, details: string, metadata: CardMetadata) => void;
};

export const NewCardForm = ({ onAdd }: NewCardFormProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [formState, setFormState] = useState(initialFormState);
  const [metadata, setMetadata] = useState<CardMetadata>(initialMetadataState);
  const [showMoreFields, setShowMoreFields] = useState(false);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!formState.title.trim()) {
      return;
    }
    onAdd(formState.title.trim(), formState.details.trim(), {
      label: metadata.label.trim(),
      dueDate: metadata.dueDate,
      assignee: metadata.assignee.trim(),
    });
    setFormState(initialFormState);
    setMetadata(initialMetadataState);
    setShowMoreFields(false);
    setIsOpen(false);
  };

  return (
    <div className="mt-4">
      {isOpen ? (
        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            value={formState.title}
            onChange={(event) =>
              setFormState((prev) => ({ ...prev, title: event.target.value }))
            }
            placeholder="Card title"
            className="w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm font-medium text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
            required
          />
          <textarea
            value={formState.details}
            onChange={(event) =>
              setFormState((prev) => ({ ...prev, details: event.target.value }))
            }
            placeholder="Details"
            rows={3}
            className="w-full resize-none rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--gray-text)] outline-none transition focus:border-[var(--primary-blue)]"
          />

          {showMoreFields ? (
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              <input
                value={metadata.label}
                onChange={(event) =>
                  setMetadata((prev) => ({ ...prev, label: event.target.value }))
                }
                placeholder="Label"
                aria-label="Card label"
                className="w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
              />
              <input
                type="date"
                value={metadata.dueDate}
                onChange={(event) =>
                  setMetadata((prev) => ({ ...prev, dueDate: event.target.value }))
                }
                aria-label="Due date"
                className="w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
              />
              <input
                value={metadata.assignee}
                onChange={(event) =>
                  setMetadata((prev) => ({ ...prev, assignee: event.target.value }))
                }
                placeholder="Assignee"
                aria-label="Assignee"
                className="w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
              />
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setShowMoreFields(true)}
              className="text-xs font-semibold text-[var(--primary-blue)] hover:underline"
            >
              + Add label, due date, or assignee
            </button>
          )}

          <div className="flex items-center gap-2">
            <button
              type="submit"
              className="inline-flex items-center gap-1.5 rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:brightness-110"
            >
              <PlusIcon className="h-3.5 w-3.5" />
              Add card
            </button>
            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                setFormState(initialFormState);
                setMetadata(initialMetadataState);
                setShowMoreFields(false);
              }}
              className="inline-flex items-center gap-1.5 rounded-full border border-[var(--stroke)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)] transition hover:text-[var(--navy-dark)]"
            >
              <XIcon className="h-3.5 w-3.5" />
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="flex w-full items-center justify-center gap-1.5 rounded-full border border-dashed border-[var(--stroke)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--primary-blue)] transition hover:border-[var(--primary-blue)]"
        >
          <PlusIcon className="h-3.5 w-3.5" />
          Add a card
        </button>
      )}
    </div>
  );
};
