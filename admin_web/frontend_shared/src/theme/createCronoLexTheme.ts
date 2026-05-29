import { createTheme } from "@mui/material/styles";
import type { PaletteMode } from "@mui/material";

const lightPalette = {
  background: {
    default: "#ffffff",
    paper: "#ffffff",
  },
  primary: {
    light: "#7578ff",
    main: "#635bff",
    dark: "#4e36f5",
    contrastText: "#ffffff",
  },
  secondary: {
    light: "#555e68",
    main: "#32383e",
    dark: "#202427",
    contrastText: "#ffffff",
  },
  success: {
    light: "#2ed3b8",
    main: "#15b79f",
    dark: "#0e9382",
    contrastText: "#ffffff",
  },
  info: {
    light: "#10bee8",
    main: "#04aad6",
    dark: "#0787b3",
    contrastText: "#ffffff",
  },
  warning: {
    light: "#ffbb1f",
    main: "#fb9c0c",
    dark: "#de7101",
    contrastText: "#ffffff",
  },
  error: {
    light: "#f97970",
    main: "#f04438",
    dark: "#de3024",
    contrastText: "#ffffff",
  },
  text: {
    primary: "#212636",
    secondary: "#667085",
    disabled: "#8a94a6",
  },
  divider: "#dcdfe4",
};

export function createCronoLexTheme(mode: PaletteMode = "dark") {
  const inputBackground = mode === "dark" ? "#11151c" : "#ffffff";
  const inputText = mode === "dark" ? "#edf1f7" : lightPalette.text.primary;
  const inputSelection = mode === "dark" ? "rgba(92, 200, 167, 0.35)" : "rgba(99, 91, 255, 0.22)";

  return createTheme({
    palette: {
      mode,
      background: {
        default: mode === "dark" ? "#111318" : lightPalette.background.default,
        paper: mode === "dark" ? "#181b22" : lightPalette.background.paper,
      },
      primary: {
        ...(mode === "dark" ? { main: "#5cc8a7", contrastText: "#071a14" } : lightPalette.primary),
      },
      secondary: {
        ...(mode === "dark" ? { main: "#9ca7b7", contrastText: "#071a14" } : lightPalette.secondary),
      },
      success: {
        ...(mode === "dark" ? { main: "#5cc8a7", contrastText: "#071a14" } : lightPalette.success),
      },
      info: {
        ...(mode === "dark" ? { main: "#66e0fa", contrastText: "#071a14" } : lightPalette.info),
      },
      warning: {
        ...(mode === "dark" ? { main: "#ffbb1f", contrastText: "#071a14" } : lightPalette.warning),
      },
      error: {
        ...(mode === "dark" ? { main: "#ff8177" } : lightPalette.error),
      },
      text: {
        primary: mode === "dark" ? "#edf1f7" : lightPalette.text.primary,
        secondary: mode === "dark" ? "#9ca7b7" : lightPalette.text.secondary,
        disabled: mode === "dark" ? "#6f7a8a" : lightPalette.text.disabled,
      },
      divider: mode === "dark" ? "rgba(255, 255, 255, 0.12)" : lightPalette.divider,
    },
    shape: {
      borderRadius: mode === "dark" ? 6 : 8,
    },
    typography: {
      fontFamily: "\"Roboto\", system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif",
      fontSize: 14,
      button: {
        textTransform: "none",
        fontWeight: 500,
      },
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          "input::selection, textarea::selection": {
            color: inputText,
            backgroundColor: inputSelection,
          },
          "input:-webkit-autofill, input:-webkit-autofill:hover, input:-webkit-autofill:focus, textarea:-webkit-autofill, textarea:-webkit-autofill:hover, textarea:-webkit-autofill:focus": {
            WebkitTextFillColor: inputText,
            caretColor: inputText,
            WebkitBoxShadow: `0 0 0 100px ${inputBackground} inset`,
            transition: "background-color 9999s ease-out 0s",
          },
          ".MuiDialogTitle-root + .MuiDialogContent-root": {
            paddingTop: "10px !important",
          },
        },
      },
      MuiButton: {
        defaultProps: {
          size: "small",
        },
        styleOverrides: {
          root: {
            minHeight: 38,
            borderRadius: mode === "dark" ? 6 : 8,
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: "none",
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            backgroundImage: "none",
            boxShadow: mode === "dark" ? "0 18px 45px rgba(0, 0, 0, 0.22)" : "0 18px 45px rgba(16, 24, 40, 0.08)",
          },
        },
      },
      MuiAppBar: {
        styleOverrides: {
          root: {
            backgroundImage: "none",
          },
        },
      },
      MuiDrawer: {
        styleOverrides: {
          paper: {
            backgroundImage: "none",
          },
        },
      },
      MuiTableContainer: {
        styleOverrides: {
          root: {
            borderRadius: 8,
          },
        },
      },
      MuiTableCell: {
        styleOverrides: {
          head: {
            fontSize: 12,
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: 0,
          },
        },
      },
    },
  });
}
