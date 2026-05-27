export type PlaceholderProps = {
  title: string;
  description?: string;
};

export function Placeholder({ title, description = "" }: PlaceholderProps) {
  return (
    <Paper component="section" className="surface placeholder" variant="outlined" sx={{ p: 3 }}>
      <Typography variant="h6" component="h2">{title}</Typography>
      {description && <Typography color="text.secondary">{description}</Typography>}
    </Paper>
  );
}
import { Paper, Typography } from "@mui/material";
