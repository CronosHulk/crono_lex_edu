import { Box, Tab, Tabs } from "@mui/material";

export type ArchiveTabsLabels = {
  all: string;
  archived: string;
};

export type ArchiveTabsProps = {
  labels: ArchiveTabsLabels;
  value: "all" | "archived";
  onChange: (value: "all" | "archived") => void;
};

export function ArchiveTabs({ labels, value, onChange }: ArchiveTabsProps) {
  return (
    <Box sx={{ borderBottom: 1, borderColor: "divider", minWidth: { xs: "100%", sm: 260 } }}>
      <Tabs
        value={value}
        onChange={(_, nextValue: "all" | "archived") => onChange(nextValue)}
        aria-label="archive filter tabs"
        textColor="primary"
        indicatorColor="primary"
      >
        <Tab value="all" label={labels.all} />
        <Tab value="archived" label={labels.archived} />
      </Tabs>
    </Box>
  );
}
