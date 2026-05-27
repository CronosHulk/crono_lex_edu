import { describe, expect, it } from "vitest";

import { clientTheme, createClientTheme } from "./clientTheme";

describe("clientTheme", () => {
  it("keeps the CronoLex dark MUI theme defaults", () => {
    expect(clientTheme.palette.mode).toBe("dark");
    expect(clientTheme.palette.primary.main).toBe("#5cc8a7");
    expect(clientTheme.shape.borderRadius).toBe(6);
    expect(clientTheme.components?.MuiButton?.defaultProps).toMatchObject({ size: "small" });
    expect(clientTheme.components?.MuiPaper?.styleOverrides?.root).toMatchObject({ backgroundImage: "none" });
  });

  it("can build a light variant for the shell toggle", () => {
    const lightTheme = createClientTheme("light");

    expect(lightTheme.palette.mode).toBe("light");
    expect(lightTheme.palette.background.default).toBe("#ffffff");
    expect(lightTheme.palette.primary.main).toBe("#635bff");
    expect(lightTheme.palette.text.primary).toBe("#212636");
    expect(lightTheme.shape.borderRadius).toBe(8);
  });
});
