export function isTrialActive(
  user: { trial_end?: string | null } | null | undefined,
  now = new Date(),
) {
  const trialEnd = parseTrialEnd(user?.trial_end);
  if (!trialEnd) return false;
  return trialEnd.getTime() > now.getTime();
}

function parseTrialEnd(value: string | null | undefined) {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed;
}
