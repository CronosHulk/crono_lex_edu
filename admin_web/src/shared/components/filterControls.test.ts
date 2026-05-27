import { describe, expect, it } from "vitest";

import { filterControlSx } from "./filterControls";

describe("filterControlSx", () => {
  it("keeps one shared filter control size", () => {
    expect(filterControlSx).toMatchObject({
      width: { xs: "100%", sm: 280 },
      maxWidth: "100%",
    });
  });
});
