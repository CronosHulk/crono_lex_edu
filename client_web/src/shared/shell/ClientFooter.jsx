import { Box, Link, Stack, Typography } from "@mui/material";
import { Send } from "lucide-react";

const LINKEDIN_URL = "https://www.linkedin.com/in/maksym-huzenko-4b8b6896/?skipRedirect=true";
const TELEGRAM_ADMIN_URL = "https://t.me/CronoLexAdmin";

export function ClientFooter({ sx }) {
  return (
    <Box
      component="footer"
      sx={{
        mt: 3,
        pt: 2,
        borderTop: 1,
        borderColor: "divider",
        color: "text.secondary",
        ...sx,
      }}
    >
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={{ xs: 1, sm: 2.5 }}
        sx={{ alignItems: { xs: "flex-start", sm: "center" }, justifyContent: "center" }}
      >
        <FooterLink
          icon={<LinkedInMark />}
          label="Розробка"
          href={LINKEDIN_URL}
          text="Maksym Huzenko"
        />
        <FooterLink
          icon={<Send size={17} />}
          label="Скарги та пропозиції"
          href={TELEGRAM_ADMIN_URL}
          text="@CronoLexAdmin"
        />
      </Stack>
    </Box>
  );
}

function LinkedInMark() {
  return (
    <Box
      component="span"
      aria-hidden="true"
      sx={{
        width: 17,
        height: 17,
        borderRadius: 0.5,
        bgcolor: "currentColor",
        color: "primary.main",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 11,
        fontWeight: 900,
        lineHeight: 1,
        fontFamily: "Arial, sans-serif",
      }}
    >
      <Box component="span" sx={{ color: "primary.contrastText", transform: "translateY(-0.5px)" }}>
        in
      </Box>
    </Box>
  );
}

function FooterLink({ icon, label, href, text }) {
  return (
    <Stack direction="row" spacing={0.75} sx={{ alignItems: "center", minWidth: 0 }}>
      <Box sx={{ display: "inline-flex", color: "primary.main", flex: "0 0 auto" }}>
        {icon}
      </Box>
      <Typography variant="caption" sx={{ fontWeight: 700, color: "text.secondary" }}>
        {label}:
      </Typography>
      <Link
        href={href}
        target="_blank"
        rel="noreferrer"
        underline="hover"
        variant="caption"
        sx={{ fontWeight: 800, minWidth: 0 }}
      >
        {text}
      </Link>
    </Stack>
  );
}
