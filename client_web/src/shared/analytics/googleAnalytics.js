import { clientApi } from "../../api/clientApi";

const GTAG_SRC = "https://www.googletagmanager.com/gtag/js";
const SCRIPT_ID = "cronolex-google-tag";

export async function installGoogleAnalytics() {
  let settings;
  try {
    settings = await clientApi("/analytics-settings");
  } catch {
    return;
  }
  const ids = [
    normalizeTrackingId(settings?.google_analytics_id),
    normalizeTrackingId(settings?.google_ads_id),
  ].filter(Boolean);
  if (!ids.length) return;

  await ensureGoogleTagScript(ids[0]);
  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function gtag() {
    window.dataLayer.push(arguments);
  };
  window.gtag("js", new Date());
  ids.forEach((id) => window.gtag("config", id));
}

function normalizeTrackingId(value) {
  return typeof value === "string" ? value.trim() : "";
}

function ensureGoogleTagScript(primaryId) {
  const existing = document.getElementById(SCRIPT_ID);
  if (existing) return Promise.resolve();

  return new Promise((resolve) => {
    const script = document.createElement("script");
    script.id = SCRIPT_ID;
    script.async = true;
    script.src = `${GTAG_SRC}?id=${encodeURIComponent(primaryId)}`;
    script.onload = () => resolve();
    script.onerror = () => resolve();
    document.head.appendChild(script);
  });
}
