import { createContext, useContext, useMemo } from "react";
import { createTranslator, intlLocaleFor, normalizeLocale } from "@cronolex/shared/i18n/projectI18n";

const ClientI18nContext = createContext({
  locale: "uk",
  intlLocale: "uk-UA",
  t: createTranslator("client", "uk"),
});

export function ClientI18nProvider({ locale, children }) {
  const normalizedLocale = normalizeLocale(locale);
  const value = useMemo(
    () => ({
      locale: normalizedLocale,
      intlLocale: intlLocaleFor(normalizedLocale),
      t: createTranslator("client", normalizedLocale),
    }),
    [normalizedLocale],
  );

  return <ClientI18nContext.Provider value={value}>{children}</ClientI18nContext.Provider>;
}

export function useClientI18n() {
  return useContext(ClientI18nContext);
}

export { normalizeLocale };
