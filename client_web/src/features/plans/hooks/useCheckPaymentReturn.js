import { useEffect, useRef, useState } from "react";

const CHECK_PAYMENT_TIMEOUT_MS = 60_000;
const CHECK_PAYMENT_RESULT_DELAY_MS = 2_000;

export function useCheckPaymentReturn({
  initialPaymentId,
  isCheckPaymentReturn,
  navigate,
  normalizeReturnTo,
  refetchPaymentHistory,
  refetchPlans,
  returnTo,
  setPaymentId,
  statusQuery,
}) {
  const [overlayOpen, setOverlayOpen] = useState(() => Boolean(isCheckPaymentReturn && initialPaymentId));
  const [phase, setPhase] = useState("waiting");
  const finishedRef = useRef(false);

  useEffect(() => {
    if (!isCheckPaymentReturn || !initialPaymentId) return undefined;
    setPaymentId(initialPaymentId);
    setOverlayOpen(true);
    setPhase("waiting");
    finishedRef.current = false;
    let resultTimer;
    const timer = window.setTimeout(() => {
      if (finishedRef.current) return;
      finishedRef.current = true;
      setPhase("timeout");
      resultTimer = window.setTimeout(() => {
        setOverlayOpen(false);
        navigate("/plans", { replace: true });
      }, CHECK_PAYMENT_RESULT_DELAY_MS);
    }, CHECK_PAYMENT_TIMEOUT_MS);
    return () => {
      window.clearTimeout(timer);
      if (resultTimer) window.clearTimeout(resultTimer);
    };
  }, [initialPaymentId, isCheckPaymentReturn, navigate, setPaymentId]);

  useEffect(() => {
    if (!overlayOpen || finishedRef.current) return undefined;
    const payload = statusQuery.data;
    const status = payload?.status;
    if (!status?.is_terminal) return undefined;
    finishedRef.current = true;
    refetchPlans?.();
    refetchPaymentHistory?.();
    setPhase(status.is_success ? "success" : "failure");
    const timer = window.setTimeout(() => {
      setOverlayOpen(false);
      if (status.is_success) {
        const target = normalizeReturnTo(payload.payment?.source_path) || returnTo;
        navigate(target || "/plans", { replace: true });
        return;
      }
      navigate("/plans", { replace: true });
    }, CHECK_PAYMENT_RESULT_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [
    navigate,
    normalizeReturnTo,
    overlayOpen,
    refetchPaymentHistory,
    refetchPlans,
    returnTo,
    statusQuery.data,
  ]);

  return { overlayOpen, phase };
}
