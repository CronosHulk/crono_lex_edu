import { Box, Breadcrumbs, Button, Chip, CircularProgress, Link, Paper, Stack, Typography } from "@mui/material";
import { ChevronRight, ExternalLink } from "lucide-react";
import type { ReactNode } from "react";
import { Link as RouterLink } from "react-router-dom";
import type { SxProps, Theme } from "@mui/material/styles";

export type ChildrenProps = {
  children: ReactNode;
};

export type CrudBreadcrumb = {
  title: string;
  path?: string;
};

export type CrudPageProps = ChildrenProps & {
  title: string;
  breadcrumbs?: CrudBreadcrumb[];
  actions?: ReactNode;
};

export function CrudPage({ title, breadcrumbs = [], actions = null, children }: CrudPageProps) {
  return (
    <Box component="section" sx={{ display: "grid", gap: 2 }}>
      <CrudPageHeader title={title} breadcrumbs={breadcrumbs} actions={actions} />
      <CrudContent>{children}</CrudContent>
    </Box>
  );
}

export type CrudPageHeaderProps = {
  title: string;
  breadcrumbs?: CrudBreadcrumb[];
  actions?: ReactNode;
};

export function CrudPageHeader({ title, breadcrumbs = [], actions = null }: CrudPageHeaderProps) {
  return (
    <Stack spacing={1}>
      {breadcrumbs.length > 0 && (
        <Breadcrumbs aria-label="breadcrumb" separator={<ChevronRight size={15} />}>
          {breadcrumbs.map((breadcrumb, index) => (
            breadcrumb.path ? (
              <Link
                key={`${breadcrumb.path}-${index}`}
                component={RouterLink}
                underline="hover"
                color="inherit"
                to={breadcrumb.path}
              >
                {breadcrumb.title}
              </Link>
            ) : (
              <Typography key={`${breadcrumb.title}-${index}`} color="text.primary" sx={{ fontWeight: 600 }}>
                {breadcrumb.title}
              </Typography>
            )
          ))}
        </Breadcrumbs>
      )}
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ alignItems: { xs: "stretch", sm: "center" }, justifyContent: "space-between" }}>
        <Typography variant="h4" component="h1" sx={{ fontWeight: 700 }}>
          {title}
        </Typography>
        {actions && <CrudToolbar>{actions}</CrudToolbar>}
      </Stack>
    </Stack>
  );
}

export function CrudContent({ children }: ChildrenProps) {
  return <Stack spacing={2}>{children}</Stack>;
}

export function CrudToolbar({ children }: ChildrenProps) {
  return <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap", justifyContent: { xs: "flex-start", sm: "flex-end" } }}>{children}</Stack>;
}

export type CrudSurfaceProps = ChildrenProps & {
  sx?: SxProps<Theme>;
};

export type CrudEditPageProps = CrudPageProps & {
  maxWidth?: string | number;
};

export function CrudEditPage({ title, breadcrumbs = [], actions = null, children, maxWidth = 920 }: CrudEditPageProps) {
  return (
    <CrudPage title={title} breadcrumbs={breadcrumbs} actions={actions}>
      <Box sx={{ width: "100%", maxWidth }}>
        {children}
      </Box>
    </CrudPage>
  );
}

export function CrudTableSurface({ children, sx }: CrudSurfaceProps) {
  return (
    <Paper variant="outlined" sx={[{ borderColor: "divider", overflow: "auto" }, ...(Array.isArray(sx) ? sx : [sx])]}>
      {children}
    </Paper>
  );
}

export function CrudFormSurface({ children, sx }: CrudSurfaceProps) {
  return (
    <Paper variant="outlined" sx={[{ width: "min(100%, 720px)", p: 2.5, borderColor: "divider" }, ...(Array.isArray(sx) ? sx : [sx])]}>
      <Stack spacing={2}>{children}</Stack>
    </Paper>
  );
}

export function ListCard({ children }: ChildrenProps) {
  return (
    <Paper variant="outlined" sx={{ p: 2, borderColor: "divider" }}>
      <Stack direction={{ xs: "column", lg: "row" }} spacing={2} sx={{ justifyContent: "space-between" }}>
        {children}
      </Stack>
    </Paper>
  );
}

export function DetailGrid({ children }: ChildrenProps) {
  return <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "repeat(3, minmax(0, 1fr))" }, gap: 2 }}>{children}</Box>;
}

export type DetailPanelProps = ChildrenProps & {
  title: string;
};

export function DetailPanel({ title, children }: DetailPanelProps) {
  return (
    <Paper variant="outlined" sx={{ p: 2, borderColor: "divider" }}>
      <Typography variant="subtitle1" sx={{ mb: 1.5 }}>{title}</Typography>
      <Stack spacing={1}>{children}</Stack>
    </Paper>
  );
}

export function InlineDetailGrid({ children }: ChildrenProps) {
  return (
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "repeat(3, minmax(0, 1fr))" }, gap: 1.5, mt: 1.5 }}>
      {children}
    </Box>
  );
}

export type InlineDetailBlockProps = ChildrenProps & {
  title: string;
};

export function InlineDetailBlock({ title, children }: InlineDetailBlockProps) {
  return (
    <Box sx={{ minWidth: 0 }}>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.75, textTransform: "uppercase" }}>
        {title}
      </Typography>
      <Stack spacing={0.75}>{children}</Stack>
    </Box>
  );
}

export function SideMeta({ children }: ChildrenProps) {
  return <Stack spacing={0.75} sx={{ minWidth: { lg: 220 } }}>{children}</Stack>;
}

export type TitleRowProps = {
  label?: string | number | null;
  title?: string | number | null;
  trailing?: ReactNode;
};

export function TitleRow({ label, title, trailing }: TitleRowProps) {
  return (
    <Stack direction="row" spacing={1} useFlexGap sx={{ alignItems: "center", flexWrap: "wrap" }}>
      <Chip label={label || "-"} size="small" variant="outlined" />
      <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{title || "-"}</Typography>
      {trailing && <Typography variant="body2" color="text.secondary">{trailing}</Typography>}
    </Stack>
  );
}

export function ActionRow({ children }: ChildrenProps) {
  return <Stack direction="row" spacing={1} useFlexGap sx={{ mt: 1, flexWrap: "wrap" }}>{children}</Stack>;
}

export function ChipRow({ children }: ChildrenProps) {
  return <Stack direction="row" spacing={0.75} useFlexGap sx={{ mt: 1, flexWrap: "wrap" }}>{children}</Stack>;
}

export type LinkButtonProps = ChildrenProps & {
  onClick: () => void;
};

export function LinkButton({ children, onClick }: LinkButtonProps) {
  return <Button size="small" variant="outlined" startIcon={<ExternalLink size={16} />} onClick={onClick}>{children}</Button>;
}

export function PreLine({ children }: ChildrenProps) {
  return <Typography variant="body2" sx={{ mt: 1, whiteSpace: "pre-line", overflowWrap: "anywhere" }}>{children || "-"}</Typography>;
}

export type EmptyStateProps = {
  text: string;
};

export function EmptyState({ text }: EmptyStateProps) {
  return <Typography color="text.secondary" sx={{ p: 2 }}>{text}</Typography>;
}

export type LoadingLineProps = {
  text: string;
};

export function LoadingLine({ text }: LoadingLineProps) {
  return (
    <Stack direction="row" spacing={1} sx={{ alignItems: "center", color: "text.secondary" }}>
      <CircularProgress size={18} />
      <Typography variant="body2">{text}</Typography>
    </Stack>
  );
}
