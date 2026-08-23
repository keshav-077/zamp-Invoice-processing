import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MatchStatePanel, POCandidateCards } from "./EvidencePanels";

describe("PO match evidence", () => {
  it("states that a weak candidate was not selected", () => {
    render(
      <>
        <MatchStatePanel
          status="NO_MATCH"
          result={{
            top_score: 0.32,
            margin: 0.05,
            matched_threshold: 0.85,
            reason: "No candidate exceeded the possible-match threshold",
          }}
        />
        <POCandidateCards
          candidates={[
            {
              po_id: "PO-1001",
              total_score: 0.32,
              selected: false,
              hard_constraints_pass: true,
              signals: [{ signal: "vendor_match", score: null }],
            },
          ]}
        />
      </>,
    );

    expect(screen.getByText("No PO matched")).toBeInTheDocument();
    expect(screen.getByText("Candidate — not selected")).toBeInTheDocument();
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
  });

  it("labels only a confirmed selection as matched", () => {
    render(
      <MatchStatePanel
        status="MATCHED"
        result={{
          selected_po_id: "PO-1001",
          top_score: 0.95,
          margin: 0.2,
          matched_threshold: 0.85,
          reason: "Confirmed",
        }}
      />,
    );

    expect(screen.getByText("Matched PO PO-1001")).toBeInTheDocument();
  });
});
