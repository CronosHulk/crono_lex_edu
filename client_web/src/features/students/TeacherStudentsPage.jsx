import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  MenuItem,
  Paper,
  Snackbar,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { Check, ExternalLink, Pencil, Plus, Video, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useLocation, useSearchParams } from "react-router-dom";

import { useClientI18n } from "../../shared/i18n/clientI18n";
import {
  googleOAuthStartUrl,
  useCreateTeacherStudentGroup,
  useCreateTeacherStudentMeetSession,
  useTeacherStudents,
  useUpdateTeacherStudentAlias,
  useUpdateTeacherStudentGroup,
  useUpdateTeacherStudentLevel,
} from "./api/studentsApi";

const PAGE_SIZE = 50;
const MEET_ERROR_TEXT = "произошла ошибка создания сесии пожалуйста попробуйте снова";

export function TeacherStudentsPage() {
  const { t } = useClientI18n();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const [googleSuccessOpen, setGoogleSuccessOpen] = useState(searchParams.get("google_auth") === "success");
  const [googleErrorOpen, setGoogleErrorOpen] = useState(searchParams.get("google_auth") === "error");
  const [googleAuthStudentId, setGoogleAuthStudentId] = useState("");
  const [meetErrorOpen, setMeetErrorOpen] = useState(false);
  const page = readPositiveInt(searchParams.get("page"), 1);
  const params = useMemo(
    () => ({
      page,
      pageSize: PAGE_SIZE,
      name: searchParams.get("name") || "",
      login: searchParams.get("login") || "",
      level: searchParams.get("level") || "",
      groupId: searchParams.get("group_id") || "",
    }),
    [page, searchParams],
  );
  const students = useTeacherStudents(params);
  const createMeet = useCreateTeacherStudentMeetSession();
  const pendingStudentId = searchParams.get("pending_action") === "create_meet" ? searchParams.get("student_id") : null;

  useEffect(() => {
    if (searchParams.get("google_auth") !== "success" || pendingStudentId || googleSuccessOpen) return;
    const next = new URLSearchParams(searchParams);
    next.delete("google_auth");
    setSearchParams(next, { replace: true });
  }, [googleSuccessOpen, pendingStudentId, searchParams, setSearchParams]);

  useEffect(() => {
    if (searchParams.get("google_auth") !== "error" || googleErrorOpen) return;
    const next = new URLSearchParams(searchParams);
    next.delete("google_auth");
    next.delete("pending_action");
    next.delete("student_id");
    setSearchParams(next, { replace: true });
  }, [googleErrorOpen, searchParams, setSearchParams]);

  useEffect(() => {
    if (searchParams.get("google_auth") !== "success" || !pendingStudentId) return;
    createMeet.mutate(pendingStudentId, {
      onSuccess: () => {
        const next = new URLSearchParams(searchParams);
        next.delete("google_auth");
        next.delete("pending_action");
        next.delete("student_id");
        setSearchParams(next, { replace: true });
      },
      onError: () => setMeetErrorOpen(true),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const updateParam = (name, value) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(name, value);
    else next.delete(name);
    next.set("page", "1");
    setSearchParams(next);
  };

  const startMeet = (studentId) => {
    createMeet.mutate(studentId, {
      onError: (error) => {
        if (error?.message === "google_auth_required") {
          setGoogleAuthStudentId(studentId);
          return;
        }
        setMeetErrorOpen(true);
      },
    });
  };

  const authReturnTo = `${location.pathname}${location.search || ""}`;
  const rows = students.data?.items || [];
  const filters = students.data?.filters || {};

  return (
    <Stack spacing={2.5}>
      {students.isError ? <Alert severity="error">{students.error?.message || t.loadError}</Alert> : null}
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
          <TextField label={t.studentName || "Ім'я"} value={params.name} onChange={(event) => updateParam("name", event.target.value)} size="small" />
          <TextField label={t.telegramLogin || "Telegram login"} value={params.login} onChange={(event) => updateParam("login", event.target.value)} size="small" />
          <TextField select label={t.level || "Рівень"} value={params.level} onChange={(event) => updateParam("level", event.target.value)} size="small" sx={{ minWidth: 120 }}>
            <MenuItem value="">{t.all || "Усі"}</MenuItem>
            {(filters.levels || []).map((level) => <MenuItem key={level.value} value={level.value}>{level.label}</MenuItem>)}
          </TextField>
          <TextField select label={t.studentGroup || "Група"} value={params.groupId} onChange={(event) => updateParam("group_id", event.target.value)} size="small" sx={{ minWidth: 180 }}>
            <MenuItem value="">{t.all || "Усі"}</MenuItem>
            {(filters.groups || []).map((group) => <MenuItem key={group.id} value={String(group.id)}>{group.title}</MenuItem>)}
          </TextField>
        </Stack>
      </Paper>

      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t.student || "Студент"}</TableCell>
              <TableCell>{t.level || "Рівень"}</TableCell>
              <TableCell>{t.dictionary || "Словник"}</TableCell>
              <TableCell>{t.meetSession || "Meet"}</TableCell>
              <TableCell>{t.studentGroup || "Група"}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((student) => (
              <StudentRow
                key={student.student_user_id}
                student={student}
                levels={filters.levels || []}
                groups={filters.groups || []}
                onCreateMeet={startMeet}
                meetPending={createMeet.isPending}
              />
            ))}
            {!students.isLoading && rows.length === 0 ? (
              <TableRow><TableCell colSpan={5}><Typography color="text.secondary">{t.noStudents || "Студентів не знайдено"}</Typography></TableCell></TableRow>
            ) : null}
          </TableBody>
        </Table>
        <TablePagination
          component="div"
          count={students.data?.total || 0}
          page={page - 1}
          rowsPerPage={PAGE_SIZE}
          rowsPerPageOptions={[PAGE_SIZE]}
          onPageChange={(_, nextPage) => updateParam("page", String(nextPage + 1))}
        />
      </TableContainer>

      <GoogleAuthDialog
        open={Boolean(googleAuthStudentId)}
        onClose={() => setGoogleAuthStudentId("")}
        authUrl={googleAuthStudentId ? googleOAuthStartUrl({ returnTo: authReturnTo, studentId: googleAuthStudentId }) : ""}
      />
      <Snackbar open={googleSuccessOpen} autoHideDuration={4000} onClose={() => setGoogleSuccessOpen(false)}>
        <Alert severity="success">{t.googleAuthSuccess || "Авторизація Google пройдена успішно"}</Alert>
      </Snackbar>
      <Snackbar open={googleErrorOpen} autoHideDuration={6000} onClose={() => setGoogleErrorOpen(false)}>
        <Alert severity="error">{t.googleAuthError || "Авторизацію Google не завершено. Спробуйте ще раз."}</Alert>
      </Snackbar>
      <Dialog open={meetErrorOpen} onClose={() => setMeetErrorOpen(false)}>
        <DialogTitle>{t.error || "Помилка"}</DialogTitle>
        <DialogContent><Typography>{MEET_ERROR_TEXT}</Typography></DialogContent>
        <DialogActions><Button onClick={() => setMeetErrorOpen(false)}>OK</Button></DialogActions>
      </Dialog>
    </Stack>
  );
}

function StudentRow({ student, levels, groups, onCreateMeet, meetPending }) {
  const { t } = useClientI18n();
  const updateAlias = useUpdateTeacherStudentAlias();
  const updateLevel = useUpdateTeacherStudentLevel();
  const updateGroup = useUpdateTeacherStudentGroup();
  const createGroup = useCreateTeacherStudentGroup();
  const [aliasEditing, setAliasEditing] = useState(false);
  const [alias, setAlias] = useState(student.teacher_alias || "");
  const [levelEditing, setLevelEditing] = useState(false);
  const [groupEditing, setGroupEditing] = useState(false);
  const [groupDialogOpen, setGroupDialogOpen] = useState(false);

  useEffect(() => setAlias(student.teacher_alias || ""), [student.teacher_alias]);

  const telegramName = [student.first_name, student.last_name].filter(Boolean).join(" ") || "-";
  const login = student.username ? `@${student.username}` : "-";
  const displayName = student.teacher_alias || telegramName;
  const stats = student.dictionary_stats || {};
  const activeMeet = student.active_meet_session;

  return (
    <TableRow hover>
      <TableCell sx={{ minWidth: 260 }}>
        {aliasEditing ? (
          <Stack direction="row" spacing={0.5} alignItems="center">
            <TextField value={alias} onChange={(event) => setAlias(event.target.value)} size="small" autoFocus />
            <IconButton size="small" onClick={() => updateAlias.mutate({ studentId: student.student_user_id, teacherAlias: alias }, { onSuccess: () => setAliasEditing(false) })}><Check size={17} /></IconButton>
            <IconButton size="small" onClick={() => setAliasEditing(false)}><X size={17} /></IconButton>
          </Stack>
        ) : (
          <Stack direction="row" spacing={1} alignItems="center">
            <Box>
              <Typography variant="body2" fontWeight={500}>{displayName}</Typography>
              <Typography variant="caption" color="text.secondary">{telegramName} ({login})</Typography>
            </Box>
            <Tooltip title={t.edit || "Редагувати"}><IconButton size="small" onClick={() => setAliasEditing(true)}><Pencil size={16} /></IconButton></Tooltip>
          </Stack>
        )}
      </TableCell>
      <TableCell sx={{ minWidth: 130 }}>
        {levelEditing ? (
          <TextField
            select
            value={student.language_level_title || ""}
            onChange={(event) => updateLevel.mutate({ studentId: student.student_user_id, languageLevel: event.target.value }, { onSuccess: () => setLevelEditing(false) })}
            size="small"
            autoFocus
          >
            {levels.map((level) => <MenuItem key={level.value} value={level.value}>{level.label}</MenuItem>)}
          </TextField>
        ) : (
          <Stack direction="row" spacing={0.5} alignItems="center">
            <Typography variant="body2">{student.language_level_title || "-"}</Typography>
            <IconButton size="small" onClick={() => setLevelEditing(true)}><Pencil size={16} /></IconButton>
          </Stack>
        )}
      </TableCell>
      <TableCell>{stats.learned_count || 0}/{stats.total_count || 0}</TableCell>
      <TableCell>
        {activeMeet?.join_url ? (
          <Button href={activeMeet.join_url} target="_blank" rel="noreferrer" variant="outlined" startIcon={<ExternalLink size={16} />}>{t.join || "Підключитися"}</Button>
        ) : (
          <Button onClick={() => onCreateMeet(student.student_user_id)} disabled={meetPending} variant="contained" startIcon={<Video size={16} />}>{t.createMeet || "Створити Meet"}</Button>
        )}
      </TableCell>
      <TableCell sx={{ minWidth: 200 }}>
        {groupEditing ? (
          <Stack direction="row" spacing={0.75}>
            <TextField
              select
              value={student.group?.id ? String(student.group.id) : ""}
              onChange={(event) => {
                if (event.target.value === "__new__") {
                  setGroupDialogOpen(true);
                  return;
                }
                updateGroup.mutate({ studentId: student.student_user_id, groupId: event.target.value ? Number(event.target.value) : null }, { onSuccess: () => setGroupEditing(false) });
              }}
              size="small"
              autoFocus
              sx={{ minWidth: 160 }}
            >
              <MenuItem value="">{t.noGroup || "Без групи"}</MenuItem>
              {groups.map((group) => <MenuItem key={group.id} value={String(group.id)}>{group.title}</MenuItem>)}
              <MenuItem value="__new__">{t.createGroup || "Створити групу"}</MenuItem>
            </TextField>
            <IconButton size="small" onClick={() => setGroupEditing(false)}><X size={17} /></IconButton>
          </Stack>
        ) : (
          <Stack direction="row" spacing={0.5} alignItems="center">
            <Typography variant="body2">{student.group?.title || t.noGroup || "Без групи"}</Typography>
            <IconButton size="small" onClick={() => setGroupEditing(true)}><Pencil size={16} /></IconButton>
          </Stack>
        )}
        <CreateGroupDialog
          open={groupDialogOpen}
          onClose={() => setGroupDialogOpen(false)}
          onCreate={(title) => createGroup.mutate({ title }, {
            onSuccess: (data) => {
              const nextGroupId = data?.group?.id;
              if (nextGroupId) updateGroup.mutate({ studentId: student.student_user_id, groupId: Number(nextGroupId) });
              setGroupDialogOpen(false);
              setGroupEditing(false);
            },
          })}
        />
      </TableCell>
    </TableRow>
  );
}

function GoogleAuthDialog({ open, onClose, authUrl }) {
  const { t } = useClientI18n();
  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>{t.googleAuthRequired || "Потрібна авторизація Google"}</DialogTitle>
      <DialogContent><Typography>{t.googleAuthHint || "Щоб створити Google Meet, підключіть Google Calendar."}</Typography></DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t.cancel || "Скасувати"}</Button>
        <Button href={authUrl} variant="contained">{t.authorizeGoogle || "Авторизувати Google"}</Button>
      </DialogActions>
    </Dialog>
  );
}

function CreateGroupDialog({ open, onClose, onCreate }) {
  const { t } = useClientI18n();
  const [title, setTitle] = useState("");
  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>{t.createGroup || "Створити групу"}</DialogTitle>
      <DialogContent>
        <TextField value={title} onChange={(event) => setTitle(event.target.value)} label={t.groupName || "Назва групи"} size="small" autoFocus sx={{ mt: 1 }} />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t.cancel || "Скасувати"}</Button>
        <Button onClick={() => onCreate(title)} disabled={!title.trim()} variant="contained" startIcon={<Plus size={16} />}>{t.create || "Створити"}</Button>
      </DialogActions>
    </Dialog>
  );
}

function readPositiveInt(value, fallback) {
  const parsed = Number.parseInt(value || "", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}
