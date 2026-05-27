import { createTheme } from "@mui/material/styles";
import type { PaletteMode } from "@mui/material";

export function createAdminTheme(mode: PaletteMode = "dark") {
  return createTheme({
    palette: {
      mode,
      background: {
        default: mode === "dark" ? "#111318" : "#f5f7fb",
        paper: mode === "dark" ? "#181b22" : "#ffffff"
      },
      primary: {
        main: "#5cc8a7",
        contrastText: "#071a14"
      },
      error: {
        main: mode === "dark" ? "#ff8177" : "#ba1a1a"
      },
      text: {
        primary: mode === "dark" ? "#edf1f7" : "#17202e",
        secondary: mode === "dark" ? "#9ca7b7" : "#607086"
      },
      divider: mode === "dark" ? "rgba(255, 255, 255, 0.12)" : "rgba(23, 32, 46, 0.14)"
    },
    shape: {
      borderRadius: 6
    },
    typography: {
      fontFamily: "\"Roboto\", system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif",
      fontSize: 14,
      button: {
        textTransform: "none",
        fontWeight: 500
      }
    },
    components: {
      MuiButton: {
        defaultProps: {
          size: "small"
        },
        styleOverrides: {
          root: {
            minHeight: 38
          }
        }
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: "none"
          }
        }
      }
    }
  });
}

export const adminTheme = createAdminTheme("dark");
