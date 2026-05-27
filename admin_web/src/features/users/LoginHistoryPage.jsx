import { useQuery } from "@tanstack/react-query";
import { Box, Typography } from "@mui/material";
import { CrudPage, Placeholder } from "../../shared/components";
import { fetchFullLoginHistory, usersQueryKeys } from "./api/usersApi";
import { LoginHistoryList } from "./components/LoginHistoryList";
import { normalizeLoginHistory } from "./loginHistory";

export function LoginHistoryPage({ t, userId }) {
  const historyQuery = useQuery({
    queryKey: usersQueryKeys.loginHistory(userId),
    queryFn: () => fetchFullLoginHistory(userId),
    enabled: Boolean(userId),
  });
  const records = normalizeLoginHistory(historyQuery.data);
  const error = historyQuery.error?.message || "";

  if (!userId) return <Placeholder title={t.loginHistory} description={t.sectionScaffold} />;

  return (
    <CrudPage
      title={t.fullLoginHistory}
      breadcrumbs={[{ title: "CronoLex", path: "/admin" }, { title: t.users, path: "/admin/users" }, { title: t.loginHistory }]}
    >
      <Box>
        <Typography variant="body2" color="text.secondary">ID: {userId}</Typography>
      </Box>
      <LoginHistoryList t={t} records={records} loading={historyQuery.isFetching} error={error} />
    </CrudPage>
  );
}
