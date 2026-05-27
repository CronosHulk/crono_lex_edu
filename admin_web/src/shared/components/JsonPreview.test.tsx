import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { formatJsonPreviewValue, hasPreviewValue, JsonPreview } from "./JsonPreview";

describe("JsonPreview", () => {
  it("does not render for empty, null, undefined, or unsupported values", () => {
    const { container, rerender } = render(<JsonPreview title="Payload" value={null} />);
    expect(container).toBeEmptyDOMElement();

    rerender(<JsonPreview title="Payload" value={undefined} />);
    expect(container).toBeEmptyDOMElement();

    rerender(<JsonPreview title="Payload" value={{}} />);
    expect(container).toBeEmptyDOMElement();

    rerender(<JsonPreview title="Payload" value="" />);
    expect(container).toBeEmptyDOMElement();

    rerender(<JsonPreview title="Payload" value="   " />);
    expect(container).toBeEmptyDOMElement();

    rerender(<JsonPreview title="Payload" value={12} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows title and formatted JSON for objects and strings", () => {
    const { rerender } = render(<JsonPreview title="Payload" value={{ ok: true, count: 2 }} />);

    expect(screen.getByText("Payload")).toBeInTheDocument();
    expect(screen.getByText((_, node) => (
      Boolean(node && node.tagName === "PRE" && node.textContent === formatJsonPreviewValue({ ok: true, count: 2 }))
    ))).toBeInTheDocument();

    rerender(<JsonPreview title="Raw" value="hello" />);

    expect(screen.getByText("Raw")).toBeInTheDocument();
    expect(screen.getByText("\"hello\"")).toBeInTheDocument();
  });

  it("exposes deterministic preview helpers", () => {
    expect(hasPreviewValue(["x"])).toBe(true);
    expect(formatJsonPreviewValue(undefined)).toBe("");
  });
});
