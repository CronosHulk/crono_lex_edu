const PROJECT_DATE_TIME_RE = /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?$/;
const ISO_DATE_TIME_RE = /^\d{4}-\d{2}-\d{2}T/;

export function formatDisplayDateTime(value, locale = "uk-UA") {
  const rawValue = normalizeDateValue(value);
  if (!rawValue) return "-";

  const projectMatch = rawValue.match(PROJECT_DATE_TIME_RE);
  if (projectMatch) {
    const [, year, month, day, hour, minute] = projectMatch;
    if (!hour || !minute) return `${day}.${month}.${year}`;
    return `${day}.${month}.${year}, ${hour}:${minute}`;
  }

  if (ISO_DATE_TIME_RE.test(rawValue)) {
    const parsed = new Date(rawValue);
    if (!Number.isNaN(parsed.getTime())) {
      return parsed.toLocaleString(locale || "uk-UA", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    }
  }

  return rawValue;
}

export function formatDisplayDate(value, locale = "uk-UA") {
  const rawValue = normalizeDateValue(value);
  if (!rawValue) return "-";

  const projectMatch = rawValue.match(PROJECT_DATE_TIME_RE);
  if (projectMatch) {
    const [, year, month, day] = projectMatch;
    return `${day}.${month}.${year}`;
  }

  if (ISO_DATE_TIME_RE.test(rawValue)) {
    const parsed = new Date(rawValue);
    if (!Number.isNaN(parsed.getTime())) {
      return parsed.toLocaleDateString(locale || "uk-UA", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      });
    }
  }

  return rawValue;
}

function normalizeDateValue(value) {
  if (value === null || value === undefined) return "";
  return String(value).trim();
}
