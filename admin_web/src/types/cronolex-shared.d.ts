declare module "@cronolex/shared/i18n/projectI18n" {
  type MessageScope = Record<string, Record<string, string>>;
  type Translator = (key: string, params?: Record<string, unknown>) => string;

  export const DEFAULT_LOCALE: string;
  export const PROJECT_MESSAGES: Record<string, MessageScope>;
  export const SUPPORTED_INTERFACE_LOCALES: readonly string[];
  export function createTranslator(scope: string, locale: string): Translator;
  export function getMessages(scope: string): MessageScope;
  export function intlLocaleFor(locale: string): string;
  export function interpolate(template: string, params?: Record<string, unknown>): string;
  export function normalizeLocale(locale?: string | null): string;
}
