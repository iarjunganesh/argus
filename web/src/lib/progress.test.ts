import { describe, expect, it } from "vitest";

import {
  MAX_UNANSWERED,
  afterStreamError,
  applyEvent,
  durationSeconds,
  finishedCount,
  initialProgress,
} from "./progress";

const at = "2026-09-28T18:18:53.429162+00:00";
const later = "2026-09-28T18:18:54.729162+00:00";

describe("applyEvent", () => {
  it("moves an agent from waiting to running to done, keeping its source", () => {
    let progress = initialProgress();
    expect(progress.identity).toEqual({ phase: "waiting", fallbacks: [] });

    progress = applyEvent(progress, { type: "agent_started", agent: "identity", at });
    expect(progress.identity.phase).toBe("running");

    progress = applyEvent(progress, {
      type: "agent_completed",
      agent: "identity",
      at: later,
      status: "completed",
      source: "fallback",
      fallbacks: ["ocr_processor[0]"],
    });
    expect(progress.identity).toEqual({
      phase: "done",
      startedAt: at,
      finishedAt: later,
      source: "fallback",
      fallbacks: ["ocr_processor[0]"],
    });
    expect(finishedCount(progress)).toBe(1);
  });

  it("marks an agent that did not complete as failed", () => {
    const progress = applyEvent(initialProgress(), {
      type: "agent_completed",
      agent: "screening",
      at,
      status: "error",
      source: "unavailable",
    });
    expect(progress.screening.phase).toBe("failed");
    expect(progress.screening.fallbacks).toEqual([]);
    expect(finishedCount(progress)).toBe(1);
  });

  it("ignores status events and agents it does not know", () => {
    const progress = initialProgress();
    expect(applyEvent(progress, { type: "status", report_id: "r", status: "completed" })).toBe(
      progress,
    );
    expect(applyEvent(progress, { type: "agent_started", agent: "oracle", at })).toBe(progress);
  });
});

describe("durationSeconds", () => {
  it("gives seconds to one decimal from the API's timestamps", () => {
    expect(durationSeconds(at, later)).toBe(1.3);
    expect(durationSeconds(later, at)).toBe(0);
    expect(durationSeconds(at)).toBeUndefined();
    expect(durationSeconds("not a time", at)).toBeUndefined();
  });
});

describe("afterStreamError", () => {
  it("keeps waiting while the API answers that the assessment is still running", () => {
    expect(afterStreamError("processing", false, 0)).toBe("wait");
  });

  it("stops waiting once the API has not answered several times in a row", () => {
    expect(afterStreamError(undefined, false, 1)).toBe("wait");
    expect(afterStreamError(undefined, false, MAX_UNANSWERED)).toBe("unreachable");
    expect(afterStreamError(undefined, true, 1)).toBe("unreachable");
  });

  it("reports an unknown ID, a finished assessment, and a stream the browser gave up on", () => {
    expect(afterStreamError("not_found", false, 0)).toBe("not_found");
    expect(afterStreamError("completed", false, 0)).toBe("finish");
    expect(afterStreamError("failed", true, 0)).toBe("finish");
    expect(afterStreamError("processing", true, 0)).toBe("unreachable");
  });
});
