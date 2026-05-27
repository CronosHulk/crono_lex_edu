export type ProviderTaskState = {
  config?: Record<string, unknown>;
  config_options?: Record<string, string[]>;
  config_options_by_provider?: Record<string, Record<string, string[]>>;
  is_enabled?: boolean;
  provider_key?: string;
};

export type ProviderTaskLabels = {
  providerDisabled?: string;
  providerEnabled?: string;
};

export function isProviderTaskEnabled(task: ProviderTaskState): boolean {
  return Boolean(task.is_enabled) && task.provider_key !== "disabled";
}

export function providerTaskEnabledLabel(task: ProviderTaskState, labels: ProviderTaskLabels): string {
  return isProviderTaskEnabled(task)
    ? labels.providerEnabled || "Enabled"
    : labels.providerDisabled || "Disabled";
}

export function providerTaskConfigOptions(task: ProviderTaskState, field: string): string[] {
  const providerKey = task.provider_key || "";
  return task.config_options_by_provider?.[providerKey]?.[field] || task.config_options?.[field] || [];
}

export function providerTaskConfigFields(task: ProviderTaskState): string[] {
  if (!task.provider_key || task.provider_key === "disabled") return [];
  const optionFields = Object.keys(task.config_options_by_provider?.[task.provider_key] || task.config_options || {});
  const configFields = Object.keys(task.config || {});
  return Array.from(new Set([...optionFields, ...configFields]));
}
