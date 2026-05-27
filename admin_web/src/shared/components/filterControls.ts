import type { SxProps, Theme } from "@mui/material/styles";

export const filterControlSx: SxProps<Theme> = {
  width: { xs: "100%", sm: 280 },
  maxWidth: "100%",
  "& .MuiInputBase-root": {
    minHeight: 56,
  },
};

export const filterActionButtonSx: SxProps<Theme> = {
  minHeight: 56,
  px: 2,
  alignSelf: { xs: "stretch", md: "center" },
};
