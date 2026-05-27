import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { CLIENT_API_BASE, clientApi } from "../../../api/clientApi";

export const teacherStudentsKey = (params: TeacherStudentsParams) => ["teacher-students", params] as const;
export const teacherStudentGroupsKey = ["teacher-student-groups"] as const;

export type TeacherStudentsParams = {
  page: number;
  pageSize: number;
  name: string;
  login: string;
  level: string;
  groupId: string;
};

export function useTeacherStudents(params: TeacherStudentsParams, enabled = true) {
  return useQuery({
    queryKey: teacherStudentsKey(params),
    queryFn: () => clientApi(`/students?${teacherStudentsSearchParams(params).toString()}`),
    placeholderData: keepPreviousData,
    enabled,
  });
}

export function useTeacherStudentGroups(enabled = true) {
  return useQuery({
    queryKey: teacherStudentGroupsKey,
    queryFn: () => clientApi("/students/groups"),
    enabled,
  });
}

export function useCreateTeacherStudentGroup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { title: string }) => clientApi("/students/groups", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: teacherStudentGroupsKey }),
  });
}

export function useUpdateTeacherStudentGroupRecord() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ groupId, title }: { groupId: number; title: string }) =>
      clientApi(`/students/groups/${groupId}`, { method: "PATCH", body: JSON.stringify({ title }) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: teacherStudentGroupsKey });
      queryClient.invalidateQueries({ queryKey: ["teacher-students"] });
    },
  });
}

export function useDeleteTeacherStudentGroup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (groupId: number) => clientApi(`/students/groups/${groupId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: teacherStudentGroupsKey });
      queryClient.invalidateQueries({ queryKey: ["teacher-students"] });
    },
  });
}

export function useUpdateTeacherStudentAlias() {
  return useStudentMutation(({ studentId, teacherAlias }: { studentId: string; teacherAlias: string }) =>
    clientApi(`/students/${studentId}/alias`, { method: "PATCH", body: JSON.stringify({ teacher_alias: teacherAlias }) }),
  );
}

export function useUpdateTeacherStudentLevel() {
  return useStudentMutation(({ studentId, languageLevel }: { studentId: string; languageLevel: string }) =>
    clientApi(`/students/${studentId}/level`, { method: "PATCH", body: JSON.stringify({ language_level: languageLevel }) }),
  );
}

export function useUpdateTeacherStudentGroup() {
  return useStudentMutation(({ studentId, groupId }: { studentId: string; groupId: number | null }) =>
    clientApi(`/students/${studentId}/group`, { method: "PATCH", body: JSON.stringify({ group_id: groupId }) }),
  );
}

export function useCreateTeacherStudentMeetSession() {
  return useStudentMutation((studentId: string) => clientApi(`/students/${studentId}/meet-session`, { method: "POST", body: "{}" }));
}

export function googleOAuthStartUrl({ returnTo, studentId }: { returnTo: string; studentId: string }) {
  const params = new URLSearchParams({
    return_to: returnTo,
    pending_action: "create_meet",
    student_id: studentId,
  });
  return `${CLIENT_API_BASE}/google/oauth/start?${params.toString()}`;
}

function useStudentMutation<TVariables>(mutationFn: (variables: TVariables) => Promise<unknown>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["teacher-students"] }),
  });
}

function teacherStudentsSearchParams(params: TeacherStudentsParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.name) query.set("name", params.name);
  if (params.login) query.set("login", params.login);
  if (params.level) query.set("level", params.level);
  if (params.groupId) query.set("group_id", params.groupId);
  return query;
}
