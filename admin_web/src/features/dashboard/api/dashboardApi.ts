import { adminApi } from "../../../api/adminApi";

export type TeacherAssignmentPayload = {
  teacherUserId: string;
  studentUserId: string;
};

export const dashboardQueryKeys = {
  all: ["dashboard"] as const,
  summary: () => [...dashboardQueryKeys.all, "summary"] as const,
};

export function fetchDashboardSummary() {
  return adminApi("/dashboard/summary");
}

export function assignTeacherStudent(payload: TeacherAssignmentPayload) {
  return adminApi("/dashboard/teacher-assignments", {
    method: "POST",
    body: JSON.stringify({
      teacher_user_id: payload.teacherUserId,
      student_user_id: payload.studentUserId,
    }),
  });
}
