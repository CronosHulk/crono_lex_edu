import { PasswordField as SharedPasswordField, PasswordRequirements as SharedPasswordRequirements } from "@cronolex/shared";

import { useClientI18n } from "../i18n/clientI18n";

export function PasswordField(props) {
  const { t } = useClientI18n();
  return <SharedPasswordField {...props} showLabel={t("showPassword")} hideLabel={t("hidePassword")} />;
}

export function PasswordRequirements({ password }) {
  const { t } = useClientI18n();
  return (
    <SharedPasswordRequirements
      password={password}
      labels={{
        length: t("minPasswordLength"),
        letters: t("latinLetters"),
        digits: t("digits"),
        special: t("specialOptional"),
      }}
    />
  );
}
