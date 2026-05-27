import type { SxProps, Theme } from "@mui/material/styles";

export const dataTableContainerSx: SxProps<Theme> = {
  position: "relative",
  borderColor: "divider",
  borderRadius: 2,
  bgcolor: "#1d1d1d",
  "& .MuiTableHead-root .MuiTableCell-root": {
    bgcolor: "#20242d",
    color: "text.primary",
    fontWeight: 700,
  },
  "& .MuiTableCell-root": {
    borderColor: "divider",
  },
  "& .MuiTableRow-hover:hover": {
    bgcolor: "action.hover",
  },
};
