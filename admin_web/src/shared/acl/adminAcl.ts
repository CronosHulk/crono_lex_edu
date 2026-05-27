export function canAdminAccess(user: unknown, action: string): boolean {
  return readCapabilities(user).includes(action);
}

export function readCapabilities(user: unknown): string[] {
  if (!user || typeof user !== "object") return [];
  const value = (user as { acl_capabilities?: unknown }).acl_capabilities;
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}
