import type { Card } from "@/lib/kanban";

type CardBadgesProps = {
  card: Card;
};

export const CardBadges = ({ card }: CardBadgesProps) => {
  if (!card.label && !card.dueDate && !card.assignee) {
    return null;
  }

  return (
    <div className="mt-3 flex flex-wrap items-center gap-1.5">
      {card.label ? (
        <span className="rounded-full bg-[var(--accent-yellow)]/20 px-2 py-0.5 text-[11px] font-semibold text-[var(--navy-dark)]">
          {card.label}
        </span>
      ) : null}
      {card.dueDate ? (
        <span className="rounded-full bg-[var(--primary-blue)]/10 px-2 py-0.5 text-[11px] font-medium text-[var(--primary-blue)]">
          Due {card.dueDate}
        </span>
      ) : null}
      {card.assignee ? (
        <span className="rounded-full bg-[var(--secondary-purple)]/10 px-2 py-0.5 text-[11px] font-medium text-[var(--secondary-purple)]">
          {card.assignee}
        </span>
      ) : null}
    </div>
  );
};
