export type UsersListSearchParams = {
  archived: boolean;
  page: number;
  pageSize: number;
  roles: string[];
  search: string;
  userId: string;
  userType: "admin" | "student" | "teacher";
};

export function usersListParamsFromSearch(searchParams: URLSearchParams): UsersListSearchParams {
  return {
    archived: searchParams.get("archived") === "true",
    page: positiveIntParam(searchParams.get("page"), 1),
    pageSize: positiveIntParam(searchParams.get("page_size"), 50),
    roles: searchParams.getAll("role"),
    search: searchParams.get("search") || "",
    userId: searchParams.get("user_id") || "",
    userType: userTypeParam(searchParams.get("user_type")),
  };
}

export function applyUsersListParamUpdates(searchParams: URLSearchParams, updates: Partial<UsersListSearchParams>): URLSearchParams {
  const next = new URLSearchParams(searchParams);
  if ("page" in updates) setSearchParam(next, "page", updates.page, 1);
  if ("pageSize" in updates) setSearchParam(next, "page_size", updates.pageSize, 50);
  if ("archived" in updates) setSearchParam(next, "archived", updates.archived, false);
  if ("search" in updates) setSearchParam(next, "search", updates.search, "");
  if ("userId" in updates) setSearchParam(next, "user_id", updates.userId, "");
  if ("userType" in updates) setSearchParam(next, "user_type", updates.userType, "student");
  if ("roles" in updates) {
    next.delete("role");
    updates.roles?.forEach((value) => next.append("role", value));
  }
  return next;
}

function userTypeParam(value: string | null): "admin" | "student" | "teacher" {
  return value === "admin" || value === "teacher" ? value : "student";
}

function positiveIntParam(value: string | null, fallback: number): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

function setSearchParam(params: URLSearchParams, key: string, value: unknown, defaultValue: unknown) {
  if (value === defaultValue || value === "" || value === null || value === undefined) {
    params.delete(key);
    return;
  }
  params.set(key, String(value));
}
