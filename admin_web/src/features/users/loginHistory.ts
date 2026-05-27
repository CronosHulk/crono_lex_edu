export type LoginHistoryResponse<T> =
  | T[]
  | {
      items?: T[];
      records?: T[];
      login_history?: T[];
    }
  | null
  | undefined;

export type UserTitleTarget = {
  first_name?: string | null;
  last_name?: string | null;
  username?: string | null;
  user_id?: string | number | null;
  user_uuid?: string | number | null;
};

export function normalizeLoginHistory<T>(data: LoginHistoryResponse<T>): T[] {
  if (Array.isArray(data)) return data;
  return data?.items || data?.records || data?.login_history || [];
}

export function formatUserTitle(target: UserTitleTarget): string {
  const name = [target.first_name, target.last_name].filter(Boolean).join(" ");
  const username = target.username ? `@${target.username}` : "";
  return [name, username, `UUID: ${target.user_id || target.user_uuid || ""}`].filter(Boolean).join(" · ");
}
