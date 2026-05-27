import { useState } from "react";
import { Bot, KeyRound, MessageCircle, Send, ShieldCheck } from "lucide-react";
import { Alert, Avatar, Box, Button, Chip, Divider, Paper, Stack, TextField, Typography } from "@mui/material";

import { clientApi as api } from "../../api/clientApi";
import { PasswordField } from "../../shared/components/PasswordControls";
import { ClientFooter } from "../../shared/shell/ClientFooter";

const TELEGRAM_BOT_URL = "https://t.me/crono_lex_bot";

export function LoginPage({ onAuthed, notice }) {
  const [step, setStep] = useState("start");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [challengeId, setChallengeId] = useState(null);
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
      setStep("otp");
    } catch (err) {
      setError(err.message);
    }
  }

  async function verifyPassword(event) {
    event.preventDefault();
    setError("");
    try {
      const data = await api("/auth/verify-password", { method: "POST", body: JSON.stringify({ username, password }) });
      setChallengeId(data.challenge_id);
      setStep("otp");
    } catch (err) {
      setError(err.message);
    }
  }

  async function verifyOtp(event) {
    event.preventDefault();
    setError("");
    try {
      const data = await api("/auth/verify-otp", {
        method: "POST",
        body: JSON.stringify({ challenge_id: challengeId, otp })
      });
      onAuthed(data);
    } catch (err) {
      setError(err.message);
    }
  }

  if (step === "otp") {
    return (
      <AuthLayout>
        <OtpForm
          error={error}
          otp={otp}
          setOtp={setOtp}
          onSubmit={verifyOtp}
        />
      </AuthLayout>
    );
  }

  return (
    <AuthLayout>
      <Paper
        component="form"
        variant="outlined"
        onSubmit={step === "password" ? verifyPassword : start}
        sx={{ p: { xs: 2.5, sm: 4 }, borderColor: "divider", borderRadius: 2 }}
      >
        <Stack spacing={2.25}>
          <AuthHeader title="Увійти в CronoLex" text="Особистий кабінет для тренувань, імпорту слів і налаштувань." />
          {notice && <Alert severity="info">{notice}</Alert>}
          {error && <Alert severity="error">{error}</Alert>}
          {step === "start" ? (
            <>
              <TextField label="Telegram login" value={username} onChange={(event) => setUsername(event.target.value)} autoFocus fullWidth />
              <Button type="submit" variant="contained" size="large" startIcon={<KeyRound size={18} />}>Продовжити</Button>
            </>
          ) : (
            <>
              <PasswordField label="Пароль" value={password} onChange={setPassword} autoFocus />
              <Button type="submit" variant="contained" size="large" startIcon={<KeyRound size={18} />}>Увійти</Button>
            </>
          )}
        </Stack>
      </Paper>
    </AuthLayout>
  );
}

function OtpForm({ error, otp, setOtp, onSubmit }) {
  return (
    <Paper
      component="form"
      variant="outlined"
      onSubmit={onSubmit}
      sx={{ p: { xs: 2.5, sm: 4 }, borderColor: "divider", borderRadius: 2 }}
    >
      <Stack spacing={2.25}>
        <AuthHeader title="Підтвердити вхід" text="Ми надіслали одноразовий код у Telegram." />
        {error && <Alert severity="error">{error}</Alert>}
        <TextField label="OTP код" value={otp} onChange={(event) => setOtp(event.target.value)} autoFocus fullWidth />
        <Button type="submit" variant="contained" size="large">Увійти</Button>
      </Stack>
    </Paper>
  );
}

function AuthLayout({ children }) {
  return (
    <Box
      className="login-shell"
      sx={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        px: { xs: 2, sm: 3 },
        py: { xs: 3, md: 5 },
        bgcolor: "background.default",
      }}
    >
      <Paper
        variant="outlined"
        sx={{
          width: "min(100%, 1040px)",
          overflow: "hidden",
          borderColor: "divider",
          borderRadius: 3,
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "minmax(320px, 0.9fr) minmax(380px, 1fr)" },
          my: "auto",
        }}
      >
        <TelegramIntro />
        <Box sx={{ p: { xs: 2, sm: 3, md: 4 }, display: "grid", alignItems: "center" }}>
          {children}
        </Box>
      </Paper>
      <ClientFooter sx={{ width: "min(100%, 1040px)", mt: "auto" }} />
    </Box>
  );
}

function TelegramIntro() {
  return (
    <Box
      sx={{
        p: { xs: 3, sm: 4 },
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        gap: 4,
        color: "primary.contrastText",
        bgcolor: "primary.main",
        backgroundImage: (theme) => theme.palette.mode === "dark"
          ? "linear-gradient(145deg, rgba(92, 200, 167, 0.96), rgba(31, 122, 103, 0.98))"
          : "linear-gradient(145deg, rgba(99, 91, 255, 0.98), rgba(35, 102, 191, 0.96))",
      }}
    >
      <Stack spacing={3}>
        <Stack direction="row" spacing={1.5} alignItems="center">
          <Avatar src="/cronolex_logo.jpg" alt="CronoLex" sx={{ width: 44, height: 44, bgcolor: "rgba(255,255,255,0.18)" }} />
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 800, lineHeight: 1.1 }}>CronoLex</Typography>
            <Typography variant="body2" sx={{ opacity: 0.78 }}>Web cabinet</Typography>
          </Box>
        </Stack>
        <Stack spacing={1.5}>
          <Chip
            icon={<Bot size={16} />}
            label="Telegram required"
            sx={{ alignSelf: "flex-start", color: "inherit", bgcolor: "rgba(255,255,255,0.14)", "& .MuiChip-icon": { color: "inherit" } }}
          />
          <Typography variant="h3" component="h2" sx={{ fontSize: "2rem", fontWeight: 850, lineHeight: 1.05 }}>
            Спочатку відкрий CronoLex у Telegram.
          </Typography>
          <Typography variant="body1" sx={{ opacity: 0.86, maxWidth: 420 }}>
            Якщо акаунта ще немає, бот створить профіль і прив&apos;яже Telegram. Після цього тут можна входити через login, пароль або OTP код.
          </Typography>
        </Stack>
      </Stack>

      <Stack spacing={1.5}>
        <IntroPoint icon={<MessageCircle />} title="Реєстрація через бот" text="Почни діалог, щоб CronoLex розпізнав твій Telegram акаунт." />
        <IntroPoint icon={<ShieldCheck />} title="OTP підтвердження" text="Код входу приходить у Telegram, без зайвих листів." />
        <Divider sx={{ borderColor: "rgba(255,255,255,0.22)" }} />
        <Button
          component="a"
          href={TELEGRAM_BOT_URL}
          target="_blank"
          rel="noreferrer"
          variant="contained"
          color="inherit"
          startIcon={<Send size={18} />}
          sx={{ alignSelf: "flex-start", color: "primary.main" }}
        >
          @crono_lex_bot
        </Button>
      </Stack>
    </Box>
  );
}

function IntroPoint({ icon, title, text }) {
  return (
    <Stack direction="row" spacing={1.5} alignItems="flex-start">
      <Box sx={{ display: "grid", placeItems: "center", width: 36, height: 36, borderRadius: 1.5, bgcolor: "rgba(255,255,255,0.14)", flexShrink: 0 }}>
        {icon}
      </Box>
      <Box>
        <Typography variant="body2" sx={{ fontWeight: 800 }}>{title}</Typography>
        <Typography variant="body2" sx={{ opacity: 0.78 }}>{text}</Typography>
      </Box>
    </Stack>
  );
}

function AuthHeader({ title, text }) {
  return (
    <Stack spacing={1}>
      <Avatar src="/cronolex_logo.jpg" alt="CronoLex" sx={{ width: 56, height: 56, bgcolor: "transparent" }} />
      <Box>
        <Typography variant="h4" component="h1" sx={{ fontWeight: 800, lineHeight: 1.15 }}>{title}</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75 }}>{text}</Typography>
      </Box>
    </Stack>
  );
}
