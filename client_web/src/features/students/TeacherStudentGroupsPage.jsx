import {
  Alert,
  Box,
  Button,
  IconButton,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { Check, Pencil, Plus, Trash2, X } from "lucide-react";
import { useState } from "react";

import { useClientI18n } from "../../shared/i18n/clientI18n";
import {
  useCreateTeacherStudentGroup,
  useDeleteTeacherStudentGroup,
  useTeacherStudentGroups,
  useUpdateTeacherStudentGroupRecord,
} from "./api/studentsApi";

export function TeacherStudentGroupsPage() {
  const { t } = useClientI18n();
  const groups = useTeacherStudentGroups();
  const createGroup = useCreateTeacherStudentGroup();
  const updateGroup = useUpdateTeacherStudentGroupRecord();
  const deleteGroup = useDeleteTeacherStudentGroup();
  const [title, setTitle] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [mutationError, setMutationError] = useState("");

  const items = groups.data?.items || [];
  const showMutationError = (error) => setMutationError(error?.message || t.saveError || "Не вдалося зберегти зміни");

  return (
    <Stack spacing={2.5}>
      {groups.isError ? <Alert severity="error">{groups.error?.message || t.loadError}</Alert> : null}
      {mutationError ? <Alert severity="error" onClose={() => setMutationError("")}>{mutationError}</Alert> : null}
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
          <TextField label={t.groupName || "Назва групи"} value={title} onChange={(event) => setTitle(event.target.value)} size="small" />
          <Button
            variant="contained"
            startIcon={<Plus size={16} />}
            disabled={!title.trim() || createGroup.isPending}
            onClick={() => createGroup.mutate(
              { title },
              {
                onSuccess: () => {
                  setTitle("");
                  setMutationError("");
                },
                onError: showMutationError,
              },
            )}
          >
            {t.createGroup || "Створити групу"}
          </Button>
        </Stack>
      </Paper>
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t.groupName || "Назва групи"}</TableCell>
              <TableCell align="right">{t.actions || "Дії"}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {items.map((group) => (
              <TableRow key={group.id} hover>
                <TableCell>
                  {editingId === group.id ? (
                    <TextField value={editingTitle} onChange={(event) => setEditingTitle(event.target.value)} size="small" autoFocus />
                  ) : (
                    <Typography variant="body2">{group.title}</Typography>
                  )}
                </TableCell>
                <TableCell align="right">
                  {editingId === group.id ? (
                    <>
                      <IconButton
                        size="small"
                        onClick={() => updateGroup.mutate(
                          { groupId: group.id, title: editingTitle },
                          {
                            onSuccess: () => {
                              setEditingId(null);
                              setMutationError("");
                            },
                            onError: showMutationError,
                          },
                        )}
                      >
                        <Check size={17} />
                      </IconButton>
                      <IconButton size="small" onClick={() => setEditingId(null)}><X size={17} /></IconButton>
                    </>
                  ) : (
                    <>
                      <IconButton size="small" onClick={() => { setEditingId(group.id); setEditingTitle(group.title); }}><Pencil size={17} /></IconButton>
                      <IconButton size="small" onClick={() => deleteGroup.mutate(group.id, { onSuccess: () => setMutationError(""), onError: showMutationError })}><Trash2 size={17} /></IconButton>
                    </>
                  )}
                </TableCell>
              </TableRow>
            ))}
            {!groups.isLoading && items.length === 0 ? (
              <TableRow><TableCell colSpan={2}><Box color="text.secondary">{t.noGroups || "Груп ще немає"}</Box></TableCell></TableRow>
            ) : null}
          </TableBody>
        </Table>
      </TableContainer>
    </Stack>
  );
}
