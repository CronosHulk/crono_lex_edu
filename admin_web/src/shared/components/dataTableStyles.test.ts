import { describe, expect, it } from "vitest";

import { dataTableContainerSx } from "./dataTableStyles";

describe("dataTableContainerSx", () => {
  it("keeps shared MUI table surface styling", () => {
    expect(dataTableContainerSx).toMatchObject({
      position: "relative",
      borderColor: "divider",
      borderRadius: 2,
      bgcolor: "#1d1d1d",
    });
  });
});
