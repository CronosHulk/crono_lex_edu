export const REMINDER_HOURS = Array.from({ length: 16 }, (_item, index) => index + 7);
export const REMINDER_MINUTES = [0, 30];
export const WEEKDAY_VALUES = [0, 1, 2, 3, 4, 5, 6];

export function normalizeReminderSchedule(schedule, profile) {
  if (Array.isArray(schedule) && schedule.length > 0) {
    return schedule.map((row) => ({
      weekday: Number(row.weekday),
      title: row.title || "",
      hour: Number(row.hour),
      minute: Number(row.minute || 0),
      status: row.status === "disabled" ? "disabled" : "enabled"
    }));
  }
  if (profile?.daily_reminder_hour === null || profile?.daily_reminder_hour === undefined) return [];
  return (profile.reminder_weekdays || []).map((weekday) => ({
    weekday: Number(weekday),
    title: "",
    hour: Number(profile.daily_reminder_hour),
    minute: 0,
    status: "enabled"
  }));
}

export function rowsToRules(rows, t) {
  const groups = new Map();
  for (const row of rows || []) {
    const minute = Number(row.minute || 0);
    const title = row.title || defaultReminderTitle(Number(row.hour), minute, t);
    const key = `${row.status}:${row.hour}:${minute}:${title}`;
    const current = groups.get(key) || {
      id: key,
      title,
      weekdays: [],
      hour: Number(row.hour),
      minute,
      status: row.status === "disabled" ? "disabled" : "enabled",
    };
    current.weekdays.push(Number(row.weekday));
    groups.set(key, current);
  }
  return [...groups.values()]
    .map((rule) => ({ ...rule, weekdays: sortedUnique(rule.weekdays) }))
    .sort((left, right) => left.hour - right.hour || left.minute - right.minute || left.weekdays[0] - right.weekdays[0]);
}

export function rulesToRows(rules) {
  return (rules || [])
    .flatMap((rule) =>
      sortedUnique(rule.weekdays).map((weekday) => ({
        weekday,
        title: rule.title,
        hour: Number(rule.hour),
        minute: Number(rule.minute || 0),
        status: rule.status === "disabled" ? "disabled" : "enabled",
      }))
    )
    .sort((left, right) => left.weekday - right.weekday || left.hour - right.hour || left.minute - right.minute);
}

export function formatTime(hour, minute = 0) {
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

export function formatDays(weekdays, t) {
  const selected = sortedUnique(weekdays);
  if (selected.length === 7) return t("reminderEveryDay");
  if (selected.length === 0) return t("reminderNoDays");
  return selected.map((weekday) => weekdayShortOptions(t).find((option) => option.value === weekday)?.full).filter(Boolean).join(", ");
}

export function weekdayShortOptions(t) {
  return [
    { value: 0, label: t("weekdayShortMonday"), full: t("weekdayMondayGenitive") },
    { value: 1, label: t("weekdayShortTuesday"), full: t("weekdayTuesdayGenitive") },
    { value: 2, label: t("weekdayShortWednesday"), full: t("weekdayWednesdayGenitive") },
    { value: 3, label: t("weekdayShortThursday"), full: t("weekdayThursdayGenitive") },
    { value: 4, label: t("weekdayShortFriday"), full: t("weekdayFridayGenitive") },
    { value: 5, label: t("weekdayShortSaturday"), full: t("weekdaySaturdayGenitive") },
    { value: 6, label: t("weekdayShortSunday"), full: t("weekdaySundayGenitive") },
  ];
}

export function defaultReminderTitle(hour, _minute, t) {
  if (hour < 12) return t("reminderMorningTitle");
  if (hour < 18) return t("reminderDayTitle");
  return t("reminderEveningTitle");
}

export function countEnabledByWeekday(rules, excludeIndex = -1) {
  const counts = new Map();
  (rules || []).forEach((rule, index) => {
    if (index === excludeIndex || rule.status === "disabled") return;
    for (const weekday of rule.weekdays || []) {
      counts.set(weekday, (counts.get(weekday) || 0) + 1);
    }
  });
  return counts;
}

export function exceedsWeekdayLimit(rules, draft, maxPerWeekday, excludeIndex = -1) {
  if (draft.status === "disabled") return false;
  const counts = countEnabledByWeekday(rules, excludeIndex);
  return (draft.weekdays || []).some((weekday) => (counts.get(weekday) || 0) + 1 > maxPerWeekday);
}

export function hasRemainingWeekdayCapacity(rules, maxPerWeekday) {
  const counts = countEnabledByWeekday(rules);
  return WEEKDAY_VALUES.some((weekday) => (counts.get(weekday) || 0) < maxPerWeekday);
}

export function hasDuplicateReminderTime(rules, draft, excludeIndex = -1) {
  const existing = new Set();
  (rules || []).forEach((rule, index) => {
    if (index === excludeIndex) return;
    for (const weekday of rule.weekdays || []) {
      existing.add(`${weekday}:${rule.hour}:${rule.minute || 0}`);
    }
  });
  return (draft.weekdays || []).some((weekday) => existing.has(`${weekday}:${draft.hour}:${draft.minute || 0}`));
}

function sortedUnique(values) {
  return [...new Set((values || []).map(Number))].filter((value) => value >= 0 && value <= 6).sort((left, right) => left - right);
}
