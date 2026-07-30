import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import { type FormEvent, useState } from "react";
import { CardBadges } from "@/components/CardBadges";
import type { Card, CardMetadata } from "@/lib/kanban";

type KanbanCardProps = {
  card: Card;
  onDelete: (cardId: string) => void;
  onEditMetadata: (cardId: string, metadata: CardMetadata) => void;
};

const metadataFromCard = (card: Card): CardMetadata => ({
  label: card.label ?? "",
  dueDate: card.dueDate ?? "",
  assignee: card.assignee ?? "",
});

export const KanbanCard = ({ card, onDelete, onEditMetadata }: KanbanCardProps) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id });

  const [isEditingMetadata, setIsEditingMetadata] = useState(false);
  const [metadataDraft, setMetadataDraft] = useState<CardMetadata>(() => metadataFromCard(card));

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const startEditingMetadata = () => {
    setMetadataDraft(metadataFromCard(card));
    setIsEditingMetadata(true);
  };

  const submitMetadata = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onEditMetadata(card.id, metadataDraft);
    setIsEditingMetadata(false);
  };

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={clsx(
        "rounded-2xl border border-transparent bg-white px-4 py-4 shadow-[0_12px_24px_rgba(3,33,71,0.08)]",
        "transition-all duration-150",
        isDragging && "opacity-60 shadow-[0_18px_32px_rgba(3,33,71,0.16)]"
      )}
      {...attributes}
      {...listeners}
      data-testid={`card-${card.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h4 className="font-display text-base font-semibold text-[var(--navy-dark)]">
            {card.title}
          </h4>
          <p className="mt-2 text-sm leading-6 text-[var(--gray-text)]">
            {card.details}
          </p>
          <CardBadges card={card} />

          {isEditingMetadata ? (
            <form
              onSubmit={submitMetadata}
              onPointerDown={(event) => event.stopPropagation()}
              className="mt-3 space-y-2 border-t border-[var(--stroke)] pt-3"
            >
              <input
                value={metadataDraft.label}
                onChange={(event) =>
                  setMetadataDraft((previous) => ({ ...previous, label: event.target.value }))
                }
                placeholder="Label"
                aria-label="Card label"
                className="w-full rounded-lg border border-[var(--stroke)] px-2 py-1 text-xs text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
              />
              <input
                type="date"
                value={metadataDraft.dueDate}
                onChange={(event) =>
                  setMetadataDraft((previous) => ({ ...previous, dueDate: event.target.value }))
                }
                aria-label="Due date"
                className="w-full rounded-lg border border-[var(--stroke)] px-2 py-1 text-xs text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
              />
              <input
                value={metadataDraft.assignee}
                onChange={(event) =>
                  setMetadataDraft((previous) => ({ ...previous, assignee: event.target.value }))
                }
                placeholder="Assignee"
                aria-label="Assignee"
                className="w-full rounded-lg border border-[var(--stroke)] px-2 py-1 text-xs text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
              />
              <div className="flex items-center gap-2">
                <button
                  type="submit"
                  className="rounded-lg bg-[var(--secondary-purple)] px-2 py-1 text-xs font-semibold text-white"
                >
                  Save
                </button>
                <button
                  type="button"
                  onClick={() => setIsEditingMetadata(false)}
                  className="text-xs font-medium text-[var(--gray-text)] hover:underline"
                >
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <button
              type="button"
              onClick={startEditingMetadata}
              onPointerDown={(event) => event.stopPropagation()}
              className="mt-2 text-xs font-semibold text-[var(--primary-blue)] hover:underline"
            >
              Edit details
            </button>
          )}
        </div>
        <button
          type="button"
          onClick={() => onDelete(card.id)}
          className="shrink-0 rounded-full p-1.5 text-[var(--gray-text)] transition hover:bg-[var(--surface)] hover:text-[var(--secondary-purple)]"
          aria-label={`Delete ${card.title}`}
          title="Delete card"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.6}
            strokeLinecap="round"
            strokeLinejoin="round"
            className="h-4 w-4"
            aria-hidden="true"
          >
            <path d="M4 5.5h12" />
            <path d="M7.5 5.5V4a1 1 0 0 1 1-1h3a1 1 0 0 1 1 1v1.5" />
            <path d="M5.5 5.5 6 15.5a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1l.5-10" />
            <path d="M8.3 8.5v5" />
            <path d="M11.7 8.5v5" />
          </svg>
        </button>
      </div>
    </article>
  );
};
