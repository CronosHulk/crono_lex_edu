import { adminApi } from "../../../api/adminApi";

export type UsersListParams = {
  archived: boolean;
  page: number;
  pageSize: number;
  roles: string[];
  search: string;
  userId: string;
  userType: "admin" | "student" | "teacher";
};

export type UserRoleMutation = {
  targetId: string | number;
  role: string;
};

export type UserLearningRoleMutation = {
  targetId: string | number;
  learningRole: string;
};

export type UserSubscriptionMutation = {
  targetId: string | number;
  planKey: string;
};

export type UserSubscriptionTrialMutation = {
  targetId: string | number;
  isTrialEnabled: boolean;
};

export const usersQueryKeys = {
  all: ["users"] as const,
  filterMetadata: () => [...usersQueryKeys.all, "filter-metadata"] as const,
  lists: () => [...usersQueryKeys.all, "list"] as const,
  list: (params: UsersListParams) => [...usersQueryKeys.lists(), params] as const,
  details: () => [...usersQueryKeys.all, "detail"] as const,
  detail: (userId: string | number | null | undefined) => [...usersQueryKeys.details(), String(userId || "")] as const,
  loginHistory: (userId: string | number | null | undefined, limit?: number) => [...usersQueryKeys.all, "login-history", String(userId || ""), limit || "all"] as const,
};

export function fetchUsers(params: UsersListParams) {
  return adminApi(`/users?${usersListSearchParams(params).toString()}`);
}

export function fetchUserFilterMetadata() {
  return adminApi("/users/filter-metadata");
}

export function updateUserRole({ targetId, role }: UserRoleMutation) {
  return adminApi(`/users/${encodeURIComponent(String(targetId))}/roles`, {
    method: "POST",
    body: JSON.stringify({ role }),
  });
}

export function updateUserLearningRole({ targetId, learningRole }: UserLearningRoleMutation) {
  return adminApi(`/users/${encodeURIComponent(String(targetId))}/learning-role`, {
    method: "POST",
    body: JSON.stringify({ learning_role: learningRole }),
  });
}

export function updateUserSubscription({ targetId, planKey }: UserSubscriptionMutation) {
  return adminApi(`/users/${encodeURIComponent(String(targetId))}/subscription`, {
    method: "POST",
    body: JSON.stringify({ plan_key: planKey }),
  });
}

export function updateUserSubscriptionTrial({ targetId, isTrialEnabled }: UserSubscriptionTrialMutation) {
  return adminApi(`/users/${encodeURIComponent(String(targetId))}/subscription-trial`, {
    method: "POST",
    body: JSON.stringify({ is_trial_enabled: isTrialEnabled }),
  });
}

export function unassignTeacherStudent(studentUserId: string | number) {
  return adminApi(`/dashboard/teacher-assignments/${encodeURIComponent(String(studentUserId))}`, {
    method: "DELETE",
  });
}

export function archiveUserById(targetId: string | number) {
  return adminApi(`/users/${encodeURIComponent(String(targetId))}/archive`, { method: "POST", body: "{}" });
}

export function deleteUserById(targetId: string | number) {
  return adminApi(`/users/${encodeURIComponent(String(targetId))}`, { method: "DELETE" });
}

export function resetUserPasswordById(targetId: string | number) {
  return adminApi(`/users/${encodeURIComponent(String(targetId))}/password-reset`, { method: "POST", body: "{}" });
}

export function fetchUserDetail(userId: string | number) {
  return adminApi(`/users/${encodeURIComponent(String(userId))}`);
}

export function fetchLatestLoginHistory(userId: string | number) {
  return adminApi(`/users/${encodeURIComponent(String(userId))}/login-history?limit=10`);
}

export function fetchFullLoginHistory(userId: string | number) {
  return adminApi(`/login-history?user_id=${encodeURIComponent(String(userId))}`);
}

function usersListSearchParams(params: UsersListParams): URLSearchParams {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
    archived: String(params.archived),
    search: params.search,
  });
  if (params.userId) query.set("user_id", params.userId);
  query.set("user_type", params.userType);
  params.roles.forEach((value) => query.append("role", value));
  return query;
}
