import { Checkbox, Chip, FormControl, InputLabel, ListItemText, MenuItem, Select, Stack } from "@mui/material";
import type { SelectChangeEvent } from "@mui/material";
import { useId } from "react";
import { filterControlSx } from "./filterControls";

export type MultiSelectOption = {
  value: string;
  label: string;
};

export type MultiSelectProps = {
  options: MultiSelectOption[];
  value: string[];
  onChange: (value: string[]) => void;
  label?: string;
};

export function normalizeMultiSelectValue(selected: string[] | string): string[] {
  return typeof selected === "string" ? selected.split(",") : selected;
}

export function MultiSelect({ options, value, onChange, label = "Фільтр" }: MultiSelectProps) {
  const labelId = useId();

  function handleChange(event: SelectChangeEvent<string[]>) {
    onChange(normalizeMultiSelectValue(event.target.value));
  }

  const selectedLabels = value
    .map((selectedValue) => options.find((option) => option.value === selectedValue)?.label || selectedValue)
    .filter(Boolean);

  return (
    <FormControl sx={filterControlSx}>
      <InputLabel id={labelId}>{label}</InputLabel>
      <Select
        labelId={labelId}
        multiple
        value={value}
        onChange={handleChange}
        label={label}
        renderValue={() => {
          return (
            <Stack direction="row" spacing={0.5} useFlexGap sx={{ flexWrap: "wrap" }}>
              {selectedLabels.map((label) => <Chip key={label} label={label} size="small" />)}
            </Stack>
          );
        }}
      >
        {options.map((option) => (
          <MenuItem key={option.value} value={option.value}>
            <Checkbox checked={value.includes(option.value)} size="small" />
            <ListItemText primary={option.label} />
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}
