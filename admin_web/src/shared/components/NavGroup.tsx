import { Box, ListItemButton, ListItemIcon, ListItemText, Stack } from "@mui/material";
import type { ReactNode } from "react";
import { Link as RouterLink } from "react-router-dom";

export type NavGroupProps = {
  icon: ReactNode;
  label: string;
  collapsed: boolean;
  to: string;
  children: ReactNode;
};

export function NavGroup({ icon, label, collapsed, to, children }: NavGroupProps) {
  return (
    <Box className="nav-group" title={collapsed ? label : ""}>
      <ListItemButton
        component={RouterLink}
        to={to}
        className="nav"
        sx={{
          width: "100%",
          minWidth: 0,
          px: 0,
          borderRadius: 1,
          color: "#9ca7b7",
          "&:hover": {
            color: "#edf1f7",
            bgcolor: "#222833"
          }
        }}
      >
        <ListItemIcon sx={{ minWidth: 56, color: "inherit", justifyContent: "center" }}>{icon}</ListItemIcon>
        {!collapsed && <ListItemText primary={label} slotProps={{ primary: { variant: "body2" } }} />}
      </ListItemButton>
      {!collapsed && <Stack className="subnav" spacing={0.5}>{children}</Stack>}
    </Box>
  );
}
