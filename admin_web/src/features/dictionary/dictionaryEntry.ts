type DictionaryRecord = Record<string, unknown>;

export const DICTIONARY_ENTRY_TYPE_OPTIONS = [
  { value: "word", label: "Word" },
  { value: "phrasal_verb", label: "Phrasal verb" },
  { value: "idiom", label: "Idiom" },
  { value: "phrase_pattern", label: "Phrase pattern" },
] as const;

export type DictionaryEntryType = typeof DICTIONARY_ENTRY_TYPE_OPTIONS[number]["value"];

export type DictionaryEntryForm = {
  word: string;
  entry_type: DictionaryEntryType;
  transcription: string;
  phonetic_us: string;
  translation_uk: string;
  translation_ru: string;
  translation_pl: string;
  examples_text: string;
};

export type DictionaryEntryPayload = {
  word: string;
  entry_type: DictionaryEntryType;
  translation_uk: string;
  translation_ru: string;
  translation_pl: string;
  examples_json: string[];
  transcription?: string;
  phonetic_us?: string;
};

export function normalizeDictionaryEntryResponse(data: unknown): DictionaryRecord | null {
  if (!isDictionaryRecord(data)) return null;
  return firstRecord(data.entry) || firstRecord(data.item) || firstRecord(data.data) || data;
}

export function buildDictionaryEntryForm(primary: DictionaryRecord | null | undefined, fallback: DictionaryRecord = {}): DictionaryEntryForm {
  const source = { ...fallback, ...(primary || {}) };
  const translations = isDictionaryRecord(source.translations) ? source.translations : {};
  return {
    word: stringValue(source.word),
    entry_type: normalizeDictionaryEntryType(source.entry_type),
    transcription: stringValue(source.transcription),
    phonetic_us: stringValue(source.phonetic_us),
    translation_uk: stringValue(source.translation_uk) || stringValue(translations.uk),
    translation_ru: stringValue(source.translation_ru) || stringValue(translations.ru),
    translation_pl: stringValue(source.translation_pl) || stringValue(translations.pl),
    examples_text: normalizeExamplesText(source.examples_json),
  };
}

export function buildDictionaryEntryPayload(form: DictionaryEntryForm, detail: DictionaryRecord | null | undefined): DictionaryEntryPayload {
  const payload: DictionaryEntryPayload = {
    word: form.word.trim(),
    entry_type: form.entry_type,
    translation_uk: form.translation_uk.trim(),
    translation_ru: form.translation_ru.trim(),
    translation_pl: form.translation_pl.trim(),
    examples_json: splitExamplesText(form.examples_text),
  };
  if (hasDictionaryField(detail, {}, "transcription")) payload.transcription = form.transcription.trim();
  if (hasDictionaryField(detail, {}, "phonetic_us")) payload.phonetic_us = form.phonetic_us.trim();
  return payload;
}

export function buildSavedDictionaryListEntry(
  listEntry: DictionaryRecord,
  detail: DictionaryRecord | null | undefined,
  form: DictionaryEntryForm,
  saved: DictionaryRecord
): DictionaryRecord {
  const examples = splitExamplesText(form.examples_text);
  return {
    ...listEntry,
    ...(detail || {}),
    ...saved,
    id: saved.id || detail?.id || listEntry.id,
    word: saved.word ?? form.word.trim(),
    entry_type: normalizeDictionaryEntryType(saved.entry_type ?? form.entry_type),
    transcription: saved.transcription ?? form.transcription,
    phonetic_us: saved.phonetic_us ?? form.phonetic_us,
    translation_uk: saved.translation_uk ?? form.translation_uk.trim(),
    translation_ru: saved.translation_ru ?? form.translation_ru.trim(),
    translation_pl: saved.translation_pl ?? form.translation_pl.trim(),
    translations_multiline: saved.translations_multiline ?? formatTranslationsMultiline(form),
    examples_json: saved.examples_json ?? examples,
  };
}

export function normalizeExamplesText(value: unknown): string {
  if (Array.isArray(value)) return value.join("\n");
  if (typeof value === "string") return value;
  return "";
}

export function formatTranslationsMultiline(form: Pick<DictionaryEntryForm, "translation_uk" | "translation_ru" | "translation_pl">): string {
  return [
    form.translation_uk && `uk: ${form.translation_uk.trim()}`,
    form.translation_ru && `ru: ${form.translation_ru.trim()}`,
    form.translation_pl && `pl: ${form.translation_pl.trim()}`,
  ].filter(Boolean).join("\n");
}

export function hasDictionaryField(primary: unknown, fallback: unknown, name: string): boolean {
  return Object.prototype.hasOwnProperty.call(primary || {}, name) || Object.prototype.hasOwnProperty.call(fallback || {}, name);
}

function firstRecord(value: unknown): DictionaryRecord | null {
  return isDictionaryRecord(value) ? value : null;
}

function isDictionaryRecord(value: unknown): value is DictionaryRecord {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function normalizeDictionaryEntryType(value: unknown): DictionaryEntryType {
  const candidate = stringValue(value);
  return DICTIONARY_ENTRY_TYPE_OPTIONS.some((option) => option.value === candidate) ? candidate as DictionaryEntryType : "word";
}

function splitExamplesText(value: string): string[] {
  return value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
}
