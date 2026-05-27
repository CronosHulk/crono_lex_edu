import { useEffect, useRef, useState } from "react";

export function useLiveImportRows({ sourceRows, jobKey, viewKey, pageSize, isPlaceholderData }) {
  const [rows, setRows] = useState([]);
  const [resolvingIds, setResolvingIds] = useState(() => new Set());
  const [newRowIds, setNewRowIds] = useState(() => new Set());
  const jobKeyRef = useRef(jobKey);
  const viewKeyRef = useRef(viewKey);
  const viewBaselinePendingRef = useRef(false);

  useEffect(() => {
    if (jobKeyRef.current !== jobKey) {
      jobKeyRef.current = jobKey;
      viewKeyRef.current = viewKey;
      viewBaselinePendingRef.current = false;
      setRows([]);
      setResolvingIds(new Set());
      setNewRowIds(new Set());
    }
  }, [jobKey, viewKey]);

  useEffect(() => {
    if (viewKeyRef.current !== viewKey) {
      viewKeyRef.current = viewKey;
      viewBaselinePendingRef.current = Boolean(isPlaceholderData);
      setRows(sourceRows.slice(0, pageSize));
      setResolvingIds(new Set());
      setNewRowIds(new Set());
      return;
    }

    if (viewBaselinePendingRef.current && !isPlaceholderData) {
      viewBaselinePendingRef.current = false;
      setRows(sourceRows.slice(0, pageSize));
      setResolvingIds(new Set());
      setNewRowIds(new Set());
      return;
    }

    setRows(sourceRows.slice(0, pageSize));
    setResolvingIds(new Set());
    setNewRowIds(new Set());
  }, [isPlaceholderData, pageSize, sourceRows, viewKey]);

  return { rows, resolvingIds, newRowIds };
}
