import { describe, expect, it } from "vitest";

import { adminTheme, createAdminTheme } from "./adminTheme";

describe("adminTheme", () => {
  it("keeps the admin shell dark and compact", () => {
    expect(adminTheme.palette.mode).toBe("dark");
    expect(adminTheme.palette.primary.main).toBe("#5cc8a7");
    expect(adminTheme.shape.borderRadius).toBe(6);
    expect(adminTheme.typography.button?.textTransform).toBe("none");
  });

  it("can build a light variant for the shell toggle", () => {
    const lightTheme = createAdminTheme("light");

    expect(lightTheme.palette.mode).toBe("light");
    expect(lightTheme.palette.background.default).toBe("#f5f7fb");
    expect(lightTheme.palette.text.primary).toBe("#17202e");
  });
});
