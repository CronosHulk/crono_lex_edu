import { Alert, Button, Paper, Stack, Typography } from "@mui/material";
import { useEffect, useState } from "react";

import { PasswordField, PasswordRequirements } from "../../shared/components/PasswordControls";
import { useClientI18n } from "../../shared/i18n/clientI18n";
import { useMarkPasswordPrompted, useUpdatePassword } from "./api/settingsApi";

export function SettingsPasswordPage({ user, onUserUpdate }) {
  const { t } = useClientI18n();
  const updatePassword = useUpdatePassword();
  const markPrompted = useMarkPasswordPrompted();
  const [currentPassword, setCurrentPassword] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const passwordMismatch = confirmPassword.length > 0 && password !== confirmPassword;
  const canSubmitPassword =
    password.length > 0 &&
    confirmPassword.length > 0 &&
    !passwordMismatch &&
    (!user?.has_password || currentPassword.length > 0);

  useEffect(() => {
    if (!user?.requires_password_setup || markPrompted.isPending || markPrompted.isSuccess) return;
    markPrompted.mutate(undefined, {
      onSuccess: (data) => onUserUpdate?.(data.user)
    });
  }, [markPrompted, onUserUpdate, user?.requires_password_setup]);

  function savePassword(event) {
    event.preventDefault();
    if (!canSubmitPassword) return;
    updatePassword.mutate(
      {
        current_password: user?.has_password ? currentPassword : null,
        password,
        confirm_password: confirmPassword
      },
      {
        onSuccess: (data) => {
          onUserUpdate?.(data.user);
          setCurrentPassword("");
          setPassword("");
          setConfirmPassword("");
        }
      }
    );
  }

  return (
    <Paper variant="outlined" sx={{ width: "min(100%, 560px)", p: { xs: 2, sm: 3 }, borderColor: "divider" }}>
      <Stack component="form" spacing={2} onSubmit={savePassword}>
        <Typography variant="h6" fontWeight={700}>{t("passwordSettingsTitle")}</Typography>
        {!user?.has_password && <Alert severity="info">{t("createPasswordLater")}</Alert>}
        {updatePassword.isSuccess && <Alert severity="success">{t("passwordSaved")}</Alert>}
        {updatePassword.isError && <Alert severity="error">{updatePassword.error.message}</Alert>}
        {user?.has_password && (
          <PasswordField label={t("currentPassword")} value={currentPassword} onChange={setCurrentPassword} />
        )}
        <PasswordField label={user?.has_password ? t("newPassword") : t("password")} value={password} onChange={setPassword} />
        <PasswordField
          label={t("confirmPassword")}
          value={confirmPassword}
          onChange={setConfirmPassword}
          error={passwordMismatch}
          helperText={passwordMismatch ? t("passwordsMismatch") : ""}
        />
        <PasswordRequirements password={password} />
        <Button type="submit" variant="contained" disabled={updatePassword.isPending || !canSubmitPassword}>
          {user?.has_password ? t("changePassword") : t("createPassword")}
        </Button>
      </Stack>
    </Paper>
  );
}
