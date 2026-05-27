import { Box, Paper, Stack } from "@mui/material";
import { Filter } from "lucide-react";
import type { ReactNode } from "react";

export type FilterBarProps = {
  children: ReactNode;
};

export function FilterBar({ children }: FilterBarProps) {
  return (
    <Paper variant="outlined" sx={{ p: 2, borderColor: "divider" }}>
      <Stack
        direction={{ xs: "column", md: "row" }}
        spacing={2.5}
        color="text.secondary"
        sx={{ alignItems: { xs: "stretch", md: "center" } }}
      >
        <Box sx={{ minHeight: 56, display: "flex", alignItems: "center" }}>
          <Filter size={20} />
        </Box>
        {children}
      </Stack>
    </Paper>
  );
}
