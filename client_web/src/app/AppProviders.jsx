import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { BrowserRouter } from "react-router-dom";
import { clientQueryClient } from "../shared/api/queryClient";
import { createClientTheme } from "../theme/clientTheme";

const THEME_STORAGE_KEY = "cronolex-client-theme";
const ThemeModeContext = createContext({ mode: "dark", toggleMode: () => {} });

export function useThemeMode() {
  return useContext(ThemeModeContext);
}

export function AppProviders({ children }) {
  const [mode, setMode] = useState(() => localStorage.getItem(THEME_STORAGE_KEY) === "light" ? "light" : "dark");
  const theme = useMemo(() => createClientTheme(mode), [mode]);

  useEffect(() => {
    localStorage.setItem(THEME_STORAGE_KEY, mode);
    document.documentElement.dataset.theme = mode;
  }, [mode]);

  const themeMode = useMemo(() => ({
    mode,
    toggleMode: () => setMode((currentMode) => currentMode === "dark" ? "light" : "dark")
  }), [mode]);

  return (
    <QueryClientProvider client={clientQueryClient}>
      <ThemeModeContext.Provider value={themeMode}>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <BrowserRouter>{children}</BrowserRouter>
        </ThemeProvider>
      </ThemeModeContext.Provider>
      {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  );
}
