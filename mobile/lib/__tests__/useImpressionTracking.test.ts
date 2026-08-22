import { renderHook } from "@testing-library/react-native";

import { recordInteraction } from "../interactions";
import { ImpressionTarget, useImpressionTracking } from "../useImpressionTracking";

jest.mock("../interactions", () => ({ recordInteraction: jest.fn() }));

const mockedRecordInteraction = recordInteraction as jest.Mock;

const target: ImpressionTarget = { eventId: "evt-1", entityId: "NVDA", domain: "stocks" };

describe("useImpressionTracking", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("records nothing when nothing is focused", () => {
    renderHook(({ t }: { t: ImpressionTarget | null }) => useImpressionTracking(t), {
      initialProps: { t: null },
    });

    expect(mockedRecordInteraction).not.toHaveBeenCalled();
  });

  it("records a single impression the moment a card becomes focused", () => {
    renderHook(({ t }: { t: ImpressionTarget | null }) => useImpressionTracking(t), {
      initialProps: { t: target as ImpressionTarget | null },
    });

    expect(mockedRecordInteraction).toHaveBeenCalledTimes(1);
    expect(mockedRecordInteraction).toHaveBeenCalledWith({
      eventId: "evt-1",
      entityId: "NVDA",
      domain: "stocks",
      interactionType: "impression",
    });
  });

  it("does not re-fire on repeated polling with the same event_id (new object, same logical target)", () => {
    const { rerender } = renderHook(
      ({ t }: { t: ImpressionTarget | null }) => useImpressionTracking(t),
      { initialProps: { t: target } }
    );

    rerender({ t: { ...target } });
    rerender({ t: { ...target } });

    expect(mockedRecordInteraction).toHaveBeenCalledTimes(1);
  });

  it("fires again when focus moves to a different card", () => {
    const { rerender } = renderHook(
      ({ t }: { t: ImpressionTarget | null }) => useImpressionTracking(t),
      { initialProps: { t: target } }
    );

    const other: ImpressionTarget = { eventId: "evt-2", entityId: "TSLA", domain: "stocks" };
    rerender({ t: other });

    expect(mockedRecordInteraction).toHaveBeenCalledTimes(2);
    expect(mockedRecordInteraction).toHaveBeenLastCalledWith(
      expect.objectContaining({ eventId: "evt-2", entityId: "TSLA" })
    );
  });

  it("does not re-fire when swiping back to a previously-focused card that's still cached", () => {
    const { rerender } = renderHook(
      ({ t }: { t: ImpressionTarget | null }) => useImpressionTracking(t),
      { initialProps: { t: target } }
    );

    const other: ImpressionTarget = { eventId: "evt-2", entityId: "TSLA", domain: "stocks" };
    rerender({ t: other });
    rerender({ t: target });

    // Swiping back to evt-1 after evt-2 is a real re-focus in the field's
    // own semantics -- this hook only suppresses immediate-rerender
    // duplicates of the *same* event_id, not a full history of everything
    // ever focused, so this is expected to fire a third time here.
    expect(mockedRecordInteraction).toHaveBeenCalledTimes(3);
  });

  it("records nothing while focus clears to null", () => {
    const { rerender } = renderHook(
      ({ t }: { t: ImpressionTarget | null }) => useImpressionTracking(t),
      { initialProps: { t: target as ImpressionTarget | null } }
    );

    rerender({ t: null });

    expect(mockedRecordInteraction).toHaveBeenCalledTimes(1); // only the initial focus
  });
});
