import { useEffect, useState } from "react";
import { CheckCircle2, Eye, EyeOff } from "lucide-react";
import { IconButton, InputAdornment, Stack, TextField } from "@mui/material";

export function PasswordField({
  label,
  value,
  onChange,
  autoFocus = false,
  error = false,
  helperText = "",
  showLabel = "Show password",
  hideLabel = "Hide password",
}) {
  const [visible, setVisible] = useState(false);
  return (
    <TextField
      label={label}
      type={visible ? "text" : "password"}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      autoFocus={autoFocus}
      fullWidth
      error={error}
      helperText={helperText}
      slotProps={{
        input: {
          endAdornment: (
            <InputAdornment position="end">
              <IconButton aria-label={visible ? hideLabel : showLabel} onClick={() => setVisible(!visible)} edge="end">
                {visible ? <EyeOff size={18} /> : <Eye size={18} />}
              </IconButton>
            </InputAdornment>
          ),
        },
      }}
    />
  );
}

export function PasswordRequirements({
  password,
  labels = {
    length: "Minimum 8 characters",
    letters: "Latin letters",
    digits: "Digits",
    special: "Special characters optional: !@#$%^&*",
  },
}) {
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
    <Stack spacing={0.75}>
      <Requirement ok={hasLength} text={labels.length} />
      <Requirement ok={hasLetter} text={labels.letters} />
      <Requirement ok={hasDigit} text={labels.digits} />
      <Requirement ok={hasSpecial || specialOptionalMet} text={labels.special} />
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
