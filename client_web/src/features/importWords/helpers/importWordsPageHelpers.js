export function buildUpgradePlanPath(location) {
  const returnTo = `${location?.pathname || "/import-words"}${location?.search || ""}${location?.hash || ""}`;
  return `/plans?return_to=${encodeURIComponent(returnTo)}`;
}

export function isSupportedGoogleDocUrl(value) {
  try {
    const url = new URL(value.trim());
    return url.protocol === "https:" && url.hostname === "docs.google.com" && Boolean(extractGoogleDocId(value));
  } catch {
    return false;
  }
}

export function extractGoogleDocId(value) {
  try {
    const url = new URL(value.trim());
    const match = url.pathname.match(/^\/document(?:\/u\/\d+)?\/d\/([^/]+)/);
    return match?.[1] || "";
  } catch {
    return "";
  }
}

export function readPositiveInt(value) {
  const parsed = Number(value || "");
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

export function readAllowedInt(value, allowedValues) {
  const parsed = readPositiveInt(value);
  return parsed && allowedValues.includes(parsed) ? parsed : null;
}

export function readAllowedValue(value, allowedValues) {
  return value && allowedValues.includes(value) ? value : null;
}

export function formatGoogleDocRescanSchedule(schedule, t) {
  const hour = readHour(schedule?.hour);
  const time = `${String(hour).padStart(2, "0")}:00`;
  const weekdays = normalizeWeekdays(schedule?.weekdays);
  if (weekdays.length === 7) {
    return t("importWordsRescanEveryDayAt", { time });
  }
  if (weekdays.length > 0) {
    return t("importWordsRescanWeekdaysAt", {
      days: weekdays.map((weekday) => weekdayLabel(weekday, t)).join(" / "),
      time,
    });
  }
  const intervalDays = readPositiveInt(schedule?.interval_days) || 3;
  return t("importWordsRescanEveryDaysAt", { days: intervalDays, time });
}

function normalizeWeekdays(weekdays) {
  if (!Array.isArray(weekdays)) return [];
  return [...new Set(weekdays.map((value) => Number(value)).filter((value) => Number.isInteger(value) && value >= 0 && value <= 6))]
    .sort((left, right) => left - right);
}

function readHour(value) {
  const parsed = Number(value ?? "");
  return Number.isInteger(parsed) && parsed >= 0 && parsed <= 23 ? parsed : 0;
}

function weekdayLabel(weekday, t) {
  const labels = [
    t("weekdayMonday"),
    t("weekdayTuesday"),
    t("weekdayWednesday"),
    t("weekdayThursday"),
    t("weekdayFriday"),
    t("weekdaySaturday"),
    t("weekdaySunday"),
  ];
  return labels[weekday] || String(weekday);
}
