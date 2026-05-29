type MessageScope = Record<string, Record<string, string>>;
type ProjectMessages = Record<string, MessageScope>;
type Translator = (key: string, params?: Record<string, unknown>) => string;

declare module "@cronolex/shared" {
  export const CRONOLEX_APP_VERSION: string;
  export const CRONOLEX_CLIENT_WEB_VERSION: string;

  export const DEFAULT_LOCALE: string;
  export const PROJECT_MESSAGES: ProjectMessages;
  export const SUPPORTED_INTERFACE_LOCALES: readonly string[];

  export function createTranslator(scope: string, locale: string): Translator;
  export function getMessages(scope: string): MessageScope;
  export function intlLocaleFor(locale: string): string;
  export function interpolate(template: string, params?: Record<string, unknown>): string;
  export function normalizeLocale(locale?: string | null): string;
  export function formatDisplayDate(value?: unknown, locale?: string): string;
  export function formatDisplayDateTime(value?: unknown, locale?: string): string;

  export const PasswordField: import("react").ComponentType<Record<string, unknown>>;
  export const PasswordRequirements: import("react").ComponentType<Record<string, unknown>>;
  export function createCronoLexTheme(
    mode?: import("@mui/material").PaletteMode,
  ): import("@mui/material").Theme;
  export const DashboardShell: import("react").ComponentType<
    Record<string, unknown> & { children?: import("react").ReactNode }
  >;
  export const LOCALE_OPTIONS: readonly { value: string; label: string }[];
}

declare module "@cronolex/shared/i18n/projectI18n" {
  export const DEFAULT_LOCALE: string;
  export const PROJECT_MESSAGES: ProjectMessages;
  export const SUPPORTED_INTERFACE_LOCALES: readonly string[];
  export function createTranslator(scope: string, locale: string): Translator;
  export function getMessages(scope: string): MessageScope;
  export function intlLocaleFor(locale: string): string;
  export function interpolate(template: string, params?: Record<string, unknown>): string;
  export function normalizeLocale(locale?: string | null): string;
}

declare module "@cronolex/shared/datetime/formatDateTime" {
  export function formatDisplayDate(value?: unknown, locale?: string): string;
  export function formatDisplayDateTime(value?: unknown, locale?: string): string;
}

declare module "@cronolex/shared/theme/createCronoLexTheme" {
  export function createCronoLexTheme(
    mode?: import("@mui/material").PaletteMode,
  ): import("@mui/material").Theme;
}
