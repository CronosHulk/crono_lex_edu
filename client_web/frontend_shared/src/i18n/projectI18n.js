import projectMessages from "./messages.json";

export const DEFAULT_LOCALE = "uk";
export const SUPPORTED_INTERFACE_LOCALES = Object.freeze(["uk", "ru", "pl"]);
export const PROJECT_MESSAGES = projectMessages;

export function getMessages(scope) {
  return projectMessages[scope] || {};
}

export function normalizeLocale(locale) {
  return SUPPORTED_INTERFACE_LOCALES.includes(locale) ? locale : DEFAULT_LOCALE;
}

export function intlLocaleFor(locale) {
  if (locale === "ru") return "ru-RU";
  if (locale === "pl") return "pl-PL";
  return "uk-UA";
}

export function createTranslator(scope, locale) {
  const messages = getMessages(scope);
  const normalizedLocale = normalizeLocale(locale);
  const dictionary = messages[normalizedLocale] || messages[DEFAULT_LOCALE] || {};
  const fallbackDictionary = messages[DEFAULT_LOCALE] || {};

  return (key, params = {}) => interpolate(dictionary[key] || fallbackDictionary[key] || key, params);
}

export function interpolate(template, params = {}) {
  return String(template).replace(/\{(\w+)\}/g, (_match, key) => String(params[key] ?? ""));
}
