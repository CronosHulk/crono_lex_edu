import { TextField } from "@mui/material";
import { filterControlSx } from "./filterControls";

export type LogToolbarLabels = {
  search: string;
};

export type LogToolbarProps = {
  t: LogToolbarLabels;
  search: string;
  onSearch: (value: string) => void;
};

export function LogToolbar({ t, search, onSearch }: LogToolbarProps) {
  return (
    <TextField
      value={search}
      onChange={(event) => onSearch(event.target.value)}
      label={t.search}
      sx={filterControlSx}
    />
  );
}
