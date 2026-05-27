import { Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Typography } from "@mui/material";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

export function OfferDialog({ open, offerText, loading, t, onClose, onAccept }) {
  const contentRef = useRef(null);
  const [atEnd, setAtEnd] = useState(false);

  useEffect(() => {
    if (open) setAtEnd(false);
  }, [open]);

  function updateScrollState() {
    const node = contentRef.current;
    if (!node) return;
    setAtEnd(node.scrollTop + node.clientHeight >= node.scrollHeight - 8);
  }

  function nextOrAccept() {
    const node = contentRef.current;
    if (!node || atEnd) {
      onAccept();
      return;
    }
    node.scrollBy({ top: node.clientHeight * 0.85, behavior: "smooth" });
    window.setTimeout(updateScrollState, 260);
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth disableRestoreFocus>
      <DialogTitle>{t("billingOfferTitle")}</DialogTitle>
      <DialogContent>
        <Box
          ref={contentRef}
          onScroll={updateScrollState}
          sx={{
            border: 1,
            borderColor: "divider",
            borderRadius: 1,
            maxHeight: "55vh",
            overflowY: "auto",
            p: 2,
          }}
        >
          {loading ? <Typography>{t("loading")}</Typography> : <OfferMarkdown text={offerText} />}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t("close")}</Button>
        <Button variant="contained" onClick={nextOrAccept}>{atEnd ? t("accept") : t("next")}</Button>
      </DialogActions>
    </Dialog>
  );
}

function OfferMarkdown({ text }) {
  return (
    <Box
      sx={{
        overflowWrap: "anywhere",
        "& > :first-of-type": { mt: 0 },
        "& > :last-child": { mb: 0 },
        "& h1": { fontSize: "1.45rem", fontWeight: 700, lineHeight: 1.25, mb: 1.5 },
        "& h2": { fontSize: "1.25rem", fontWeight: 700, lineHeight: 1.3, mt: 2.5, mb: 1 },
        "& h3": { fontSize: "1.05rem", fontWeight: 700, lineHeight: 1.35, mt: 2, mb: 0.75 },
        "& p": { mb: 1.25 },
        "& ul, & ol": { pl: 3, mb: 1.5 },
        "& li": { mb: 0.5 },
        "& a": { color: "primary.main" },
        "& code": {
          bgcolor: "action.hover",
          borderRadius: 0.5,
          fontFamily: "Roboto Mono, monospace",
          px: 0.5,
        },
      }}
    >
      <ReactMarkdown>{text}</ReactMarkdown>
    </Box>
  );
}
