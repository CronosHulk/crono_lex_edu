import type { PaletteMode } from "@mui/material";
import { createCronoLexTheme } from "@cronolex/shared/theme/createCronoLexTheme";

export function createClientTheme(mode: PaletteMode = "dark") {
  return createCronoLexTheme(mode);
}

export const clientTheme = createClientTheme("dark");
