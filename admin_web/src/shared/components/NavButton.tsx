import { ListItemButton, ListItemIcon, ListItemText } from "@mui/material";
import type { ReactNode } from "react";
import { Link as RouterLink } from "react-router-dom";

export type NavButtonProps = {
  icon: ReactNode;
  label: string;
  active: boolean;
  collapsed: boolean;
  to: string;
};

export function NavButton({ icon, label, active, collapsed, to }: NavButtonProps) {
  return (
    <ListItemButton
      component={RouterLink}
      to={to}
      className={active ? "nav active" : "nav"}
      title={collapsed ? label : ""}
      sx={{
        width: "100%",
        minWidth: 0,
        px: 0,
        borderRadius: 1,
        color: active ? "#edf1f7" : "#9ca7b7",
        bgcolor: active ? "#222833" : "transparent",
        "&:hover": {
          color: "#edf1f7",
          bgcolor: "#222833"
        }
      }}
    >
      <ListItemIcon sx={{ minWidth: 56, color: "inherit", justifyContent: "center" }}>{icon}</ListItemIcon>
      {!collapsed && <ListItemText primary={label} slotProps={{ primary: { variant: "body2" } }} />}
    </ListItemButton>
  );
}
