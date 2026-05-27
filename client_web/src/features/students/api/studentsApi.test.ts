import { describe, expect, it, vi } from "vitest";

import { CLIENT_API_BASE, clientApi } from "../../../api/clientApi";
import {
  googleOAuthStartUrl,
  teacherStudentGroupsKey,
  teacherStudentsKey,
  useCreateTeacherStudentGroup,
  useCreateTeacherStudentMeetSession,
  useDeleteTeacherStudentGroup,
  useTeacherStudentGroups,
  useTeacherStudents,
  useUpdateTeacherStudentAlias,
  useUpdateTeacherStudentGroup,
  useUpdateTeacherStudentGroupRecord,
  useUpdateTeacherStudentLevel,
} from "./studentsApi";

const invalidateQueries = vi.fn();
const useMutationMock = vi.fn((config) => config);
const useQueryMock = vi.fn((config) => config);

vi.mock("@tanstack/react-query", () => ({
  keepPreviousData: Symbol.for("keepPreviousData"),
  useMutation: (config: unknown) => useMutationMock(config),
  useQuery: (config: unknown) => useQueryMock(config),
  useQueryClient: () => ({ invalidateQueries }),
}));

vi.mock("../../../api/clientApi", () => ({
  CLIENT_API_BASE: "/api/v1/client-web",
  clientApi: vi.fn(),
}));

describe("students api hooks", () => {
  const params = { page: 2, pageSize: 50, name: "Ada", login: "ada", level: "A1", groupId: "7" };

  it("builds the students query with filters", () => {
    const query = useTeacherStudents(params) as unknown as {
      enabled: boolean;
      placeholderData: symbol;
      queryFn: () => unknown;
      queryKey: readonly unknown[];
    };

    expect(query.queryKey).toEqual(teacherStudentsKey(params));
    expect(query.enabled).toBe(true);
    expect(query.placeholderData).toBe(Symbol.for("keepPreviousData"));
    query.queryFn();
    expect(clientApi).toHaveBeenCalledWith("/students?page=2&page_size=50&name=Ada&login=ada&level=A1&group_id=7");
  });

  it("builds the students query without optional filters", () => {
    const query = useTeacherStudents({ page: 1, pageSize: 50, name: "", login: "", level: "", groupId: "" }) as unknown as {
      queryFn: () => unknown;
    };

    query.queryFn();

    expect(clientApi).toHaveBeenCalledWith("/students?page=1&page_size=50");
  });

  it("builds the group list query", () => {
    const query = useTeacherStudentGroups(false) as unknown as {
      enabled: boolean;
      queryFn: () => unknown;
      queryKey: readonly unknown[];
    };

    expect(query.queryKey).toEqual(teacherStudentGroupsKey);
    expect(query.enabled).toBe(false);
    query.queryFn();
    expect(clientApi).toHaveBeenCalledWith("/students/groups");
  });

  it("creates, updates, and deletes groups", () => {
    const createMutation = useCreateTeacherStudentGroup() as unknown as { mutationFn: (payload: { title: string }) => unknown; onSuccess: () => void };
    createMutation.mutationFn({ title: "Morning" });
    createMutation.onSuccess();
    expect(clientApi).toHaveBeenCalledWith("/students/groups", { method: "POST", body: JSON.stringify({ title: "Morning" }) });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: teacherStudentGroupsKey });

    const updateMutation = useUpdateTeacherStudentGroupRecord() as unknown as { mutationFn: (payload: { groupId: number; title: string }) => unknown; onSuccess: () => void };
    updateMutation.mutationFn({ groupId: 7, title: "Evening" });
    updateMutation.onSuccess();
    expect(clientApi).toHaveBeenCalledWith("/students/groups/7", { method: "PATCH", body: JSON.stringify({ title: "Evening" }) });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["teacher-students"] });

    const deleteMutation = useDeleteTeacherStudentGroup() as unknown as { mutationFn: (groupId: number) => unknown; onSuccess: () => void };
    deleteMutation.mutationFn(7);
    deleteMutation.onSuccess();
    expect(clientApi).toHaveBeenCalledWith("/students/groups/7", { method: "DELETE" });
  });

  it("updates student fields and invalidates student queries", () => {
    const aliasMutation = useUpdateTeacherStudentAlias() as unknown as { mutationFn: (payload: { studentId: string; teacherAlias: string }) => unknown; onSuccess: () => void };
    aliasMutation.mutationFn({ studentId: "student-1", teacherAlias: "Ada L." });
    aliasMutation.onSuccess();
    expect(clientApi).toHaveBeenCalledWith("/students/student-1/alias", { method: "PATCH", body: JSON.stringify({ teacher_alias: "Ada L." }) });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["teacher-students"] });

    const levelMutation = useUpdateTeacherStudentLevel() as unknown as { mutationFn: (payload: { studentId: string; languageLevel: string }) => unknown };
    levelMutation.mutationFn({ studentId: "student-1", languageLevel: "A2" });
    expect(clientApi).toHaveBeenCalledWith("/students/student-1/level", { method: "PATCH", body: JSON.stringify({ language_level: "A2" }) });

    const groupMutation = useUpdateTeacherStudentGroup() as unknown as { mutationFn: (payload: { studentId: string; groupId: number | null }) => unknown };
    groupMutation.mutationFn({ studentId: "student-1", groupId: null });
    expect(clientApi).toHaveBeenCalledWith("/students/student-1/group", { method: "PATCH", body: JSON.stringify({ group_id: null }) });
  });

  it("creates meet sessions and OAuth start urls", () => {
    const meetMutation = useCreateTeacherStudentMeetSession() as unknown as { mutationFn: (studentId: string) => unknown };

    meetMutation.mutationFn("student-1");

    expect(clientApi).toHaveBeenCalledWith("/students/student-1/meet-session", { method: "POST", body: "{}" });
    expect(googleOAuthStartUrl({ returnTo: "/students?name=Ada", studentId: "student-1" })).toBe(
      `${CLIENT_API_BASE}/google/oauth/start?return_to=%2Fstudents%3Fname%3DAda&pending_action=create_meet&student_id=student-1`,
    );
  });
});
