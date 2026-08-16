// @vitest-environment node
import { describe, expect, it } from "vitest";

import {
  confidenceColor,
  DIMENSION_LABELS,
  directionLabel,
  formatDate,
  provenanceColor,
  scoreLabel,
  scoreTone,
} from "./format";

describe("confidenceColor", () => {
  it("maps each confidence level to a css var", () => {
    expect(confidenceColor("high")).toBe("var(--green)");
    expect(confidenceColor("moderate")).toBe("var(--yellow)");
    expect(confidenceColor("low")).toBe("var(--red)");
    expect(confidenceColor("insufficient")).toBe("var(--text-muted)");
    expect(confidenceColor("weird")).toBe("var(--text-muted)");
  });
});

describe("directionLabel", () => {
  it("describes each direction", () => {
    expect(directionLabel("higher_is_better")).toBe("Higher is better");
    expect(directionLabel("lower_is_better")).toBe("Lower is better");
    expect(directionLabel("descriptive")).toBe("Descriptive");
  });
});

describe("provenanceColor", () => {
  it("maps provenance to a css var", () => {
    expect(provenanceColor("observed")).toBe("var(--green)");
    expect(provenanceColor("rule-derived")).toBe("var(--teal)");
    expect(provenanceColor("suggested")).toBe("var(--yellow)");
    expect(provenanceColor("user")).toBe("var(--purple)");
    expect(provenanceColor("user-confirmed")).toBe("var(--purple)");
    expect(provenanceColor("other")).toBe("var(--text-muted)");
  });
});

describe("formatDate", () => {
  it("handles null", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate("")).toBe("—");
  });
  it("formats an ISO timestamp", () => {
    const out = formatDate("2026-08-01T12:00:00Z");
    expect(out).toContain("2026");
    expect(out).toContain("Aug");
  });
});

describe("scoreTone", () => {
  it("classifies scores", () => {
    expect(scoreTone(90)).toBe("good");
    expect(scoreTone(70)).toBe("good");
    expect(scoreTone(60)).toBe("warn");
    expect(scoreTone(45)).toBe("warn");
    expect(scoreTone(20)).toBe("bad");
    expect(scoreTone(null)).toBe("unknown");
  });
});

describe("scoreLabel", () => {
  it("shows placeholder for withheld scores", () => {
    expect(scoreLabel(null)).toBe("—");
    expect(scoreLabel(64)).toBe("64");
  });
});

describe("DIMENSION_LABELS", () => {
  it("covers all 8 DNA dimensions", () => {
    expect(Object.keys(DIMENSION_LABELS)).toHaveLength(8);
    expect(DIMENSION_LABELS.maintainability).toBe("Maintainability");
  });
});
