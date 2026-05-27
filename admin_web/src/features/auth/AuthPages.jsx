import { useEffect, useState } from "react";
import { CheckCircle2, Eye, EyeOff, KeyRound } from "lucide-react";
import { Alert, Avatar, Box, Button, IconButton, InputAdornment, Paper, Stack, TextField, Typography } from "@mui/material";

import { adminApi as api } from "../../api/adminApi";

export function LoginPage({ t, notice, onAuthed }) {
  const [step, setStep] = useState("start");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [challengeId, setChallengeId] = useState(null);
  const [devHint, setDevHint] = useState(null);
  const [error, setError] = useState("");

  async function start(event) {
    event.preventDefault();
    setError("");
    try {
      const data = await api("/auth/start", { method: "POST", body: JSON.stringify({ username }) });
      if (data.requires_password) {
        setStep("password");
        return;
      }
      setChallengeId(data.challenge_id);
      setDevHint(data.dev_otp_hint);
      setStep("otp");
    } catch (err) {
      setError(err.message);
    }
  }

  async function verifyPassword(event) {
    event.preventDefault();
    setError("");
    try {
      const data = await api("/auth/start", { method: "POST", body: JSON.stringify({ username, password }) });
      setChallengeId(data.challenge_id);
      setDevHint(data.dev_otp_hint);
      setStep("otp");
    } catch (err) {
      setError(err.message);
    }
  }

  async function verify(event) {
    event.preventDefault();
    setError("");
    try {
      const data = await api("/auth/verify-otp", { method: "POST", body: JSON.stringify({ challenge_id: challengeId, otp }) });
      await onAuthed(data);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <Box className="login-shell" sx={{ minHeight: "100vh", display: "grid", placeItems: "center", p: 2 }}>
      <Paper className="login" component="form" variant="outlined" onSubmit={step === "start" ? start : step === "password" ? verifyPassword : verify} sx={{ width: "min(100%, 420px)", p: 3, borderColor: "divider" }}>
        <Stack spacing={2}>
          <Avatar className="login-logo" src="/cronolex_logo.jpg" alt="CronoLex" sx={{ width: 56, height: 56, bgcolor: "transparent" }} />
          <Typography variant="h5" component="h1" fontWeight={700}>CronoLex Admin</Typography>
          {notice && <Alert severity="info">{notice}</Alert>}
          {error && <Alert severity="error">{error}</Alert>}
        {step === "start" ? (
          <>
            <TextField label={t.username} value={username} onChange={(e) => setUsername(e.target.value)} autoFocus fullWidth />
            <Button type="submit" variant="contained" startIcon={<KeyRound size={18} />}>{t.login}</Button>
          </>
        ) : step === "password" ? (
          <>
            <PasswordField label={t.password} value={password} onChange={setPassword} autoFocus />
            <Button type="submit" variant="contained" startIcon={<KeyRound size={18} />}>{t.login}</Button>
          </>
        ) : (
          <>
            {devHint && <Alert severity="info">Dev OTP: {devHint}</Alert>}
            <TextField label={t.otp} value={otp} onChange={(e) => setOtp(e.target.value)} autoFocus fullWidth />
            <Button type="submit" variant="contained" startIcon={<KeyRound size={18} />}>{t.verify}</Button>
          </>
        )}
        </Stack>
      </Paper>
    </Box>
  );
}

export function PasswordSetup({ t, onDone }) {
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      await api("/auth/set-password", { method: "POST", body: JSON.stringify({ password, confirm_password: confirmPassword }) });
      onDone();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <Box className="login-shell" sx={{ minHeight: "100vh", display: "grid", placeItems: "center", p: 2 }}>
      <Paper className="login" component="form" variant="outlined" onSubmit={submit} sx={{ width: "min(100%, 420px)", p: 3, borderColor: "divider" }}>
        <Stack spacing={2}>
          <Avatar className="login-logo" src="/cronolex_logo.jpg" alt="CronoLex" sx={{ width: 56, height: 56, bgcolor: "transparent" }} />
          <Typography variant="h5" component="h1" fontWeight={700}>{t.setPassword}</Typography>
          {error && <Alert severity="error">{error}</Alert>}
          <PasswordField label={t.password} value={password} onChange={setPassword} autoFocus />
          <PasswordField label={t.confirmPassword || "Підтвердження пароля"} value={confirmPassword} onChange={setConfirmPassword} />
          <PasswordRequirements password={password} t={t} />
          <Button type="submit" variant="contained">{t.setPassword}</Button>
        </Stack>
      </Paper>
    </Box>
  );
}

function PasswordField({ label, value, onChange, autoFocus = false }) {
  const [visible, setVisible] = useState(false);
  return (
    <TextField
      label={label}
      type={visible ? "text" : "password"}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      autoFocus={autoFocus}
      fullWidth
      slotProps={{
        input: {
          endAdornment: (
            <InputAdornment position="end">
              <IconButton aria-label={visible ? "Hide password" : "Show password"} onClick={() => setVisible(!visible)} edge="end">
                {visible ? <EyeOff size={18} /> : <Eye size={18} />}
              </IconButton>
            </InputAdornment>
          )
        }
      }}
    />
  );
}

function PasswordRequirements({ password, t }) {
  const [specialOptionalMet, setSpecialOptionalMet] = useState(false);
  const hasLength = password.length >= 8;
  const hasLetter = /[A-Za-z]/.test(password);
  const hasDigit = /\d/.test(password);
  const hasSpecial = /[!@#$%^&*()_\-+=[\]{};:'",.<>/?\\|`~]/.test(password);

  useEffect(() => {
    if (hasSpecial) {
      setSpecialOptionalMet(true);
      return undefined;
    }
    setSpecialOptionalMet(false);
    const timer = window.setTimeout(() => setSpecialOptionalMet(true), 3000);
    return () => window.clearTimeout(timer);
  }, [hasSpecial, password]);

  return (
    <Stack spacing={0.75} aria-label={t.passwordHint}>
      <Requirement ok={hasLength} text={t.passwordRuleLength || "Мінімум 8 символів"} />
      <Requirement ok={hasLetter} text={t.passwordRuleLetters || "Латинські літери"} />
      <Requirement ok={hasDigit} text={t.passwordRuleDigits || "Цифри"} />
      <Requirement ok={hasSpecial || specialOptionalMet} text={t.passwordRuleSpecial || "Спецсимволи опціонально: !@#$%^&*"} />
    </Stack>
  );
}

function Requirement({ ok, text }) {
  return (
    <Stack direction="row" spacing={1} alignItems="center" sx={{ color: ok ? "success.main" : "text.secondary", fontSize: 13 }}>
      <CheckCircle2 size={16} />
      <span>{text}</span>
    </Stack>
  );
}
