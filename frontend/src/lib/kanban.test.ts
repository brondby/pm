import { applyCardMetadata, moveCard, type Card, type Column } from "@/lib/kanban";

describe("moveCard", () => {
  const baseColumns: Column[] = [
    { id: "col-a", title: "A", cardIds: ["card-1", "card-2"] },
    { id: "col-b", title: "B", cardIds: ["card-3"] },
  ];

  it("reorders cards in the same column", () => {
    const result = moveCard(baseColumns, "card-2", "card-1");
    expect(result[0].cardIds).toEqual(["card-2", "card-1"]);
  });

  it("moves cards to another column", () => {
    const result = moveCard(baseColumns, "card-2", "card-3");
    expect(result[0].cardIds).toEqual(["card-1"]);
    expect(result[1].cardIds).toEqual(["card-2", "card-3"]);
  });

  it("drops cards to the end of a column", () => {
    const result = moveCard(baseColumns, "card-1", "col-b");
    expect(result[0].cardIds).toEqual(["card-2"]);
    expect(result[1].cardIds).toEqual(["card-3", "card-1"]);
  });
});

describe("applyCardMetadata", () => {
  const baseCard: Card = { id: "card-1", title: "Plan release", details: "Draft milestones." };

  it("sets label, dueDate, and assignee when provided", () => {
    const result = applyCardMetadata(baseCard, {
      label: "Urgent",
      dueDate: "2026-08-15",
      assignee: "Alex",
    });

    expect(result).toEqual({
      id: "card-1",
      title: "Plan release",
      details: "Draft milestones.",
      label: "Urgent",
      dueDate: "2026-08-15",
      assignee: "Alex",
    });
  });

  it("leaves title and details untouched", () => {
    const result = applyCardMetadata(baseCard, { label: "Urgent", dueDate: "", assignee: "" });
    expect(result.title).toBe("Plan release");
    expect(result.details).toBe("Draft milestones.");
  });

  it("clears an existing field when given an empty string", () => {
    const cardWithMetadata: Card = { ...baseCard, label: "Urgent", dueDate: "2026-08-15", assignee: "Alex" };

    const result = applyCardMetadata(cardWithMetadata, { label: "", dueDate: "", assignee: "" });

    expect(result.label).toBeUndefined();
    expect(result.dueDate).toBeUndefined();
    expect(result.assignee).toBeUndefined();
  });

  it("does not mutate the original card", () => {
    const original = { ...baseCard };
    applyCardMetadata(baseCard, { label: "Urgent", dueDate: "", assignee: "" });
    expect(baseCard).toEqual(original);
  });
});
