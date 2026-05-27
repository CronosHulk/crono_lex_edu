import { describe, expect, it } from "vitest";

import {
  buildDictionaryEntryForm,
  buildDictionaryEntryPayload,
  buildSavedDictionaryListEntry,
  formatTranslationsMultiline,
  hasDictionaryField,
  normalizeDictionaryEntryResponse,
  normalizeExamplesText,
  type DictionaryEntryForm,
} from "./dictionaryEntry";

const baseForm: DictionaryEntryForm = {
  word: " take off ",
  entry_type: "phrasal_verb",
  transcription: " tr ",
  phonetic_us: " us ",
  translation_uk: " злітати ",
  translation_ru: " взлетать ",
  translation_pl: " startowac ",
  examples_text: " first example \n\n second example \r\n",
};

describe("dictionary entry helpers", () => {
  it("normalizes entry response envelopes", () => {
    const entry = { id: 1, word: "entry" };
    const item = { id: 2, word: "item" };
    const data = { id: 3, word: "data" };
    const plain = { id: 4, word: "plain" };

    expect(normalizeDictionaryEntryResponse(null)).toBeNull();
    expect(normalizeDictionaryEntryResponse([])).toBeNull();
    expect(normalizeDictionaryEntryResponse({ entry })).toBe(entry);
    expect(normalizeDictionaryEntryResponse({ item })).toBe(item);
    expect(normalizeDictionaryEntryResponse({ data })).toBe(data);
    expect(normalizeDictionaryEntryResponse(plain)).toBe(plain);
    expect(normalizeDictionaryEntryResponse({ entry: "bad", item: 0, data: null })).toEqual({ entry: "bad", item: 0, data: null });
  });

  it("builds form values from primary, fallback, and nested translations", () => {
    expect(buildDictionaryEntryForm({
      word: "word",
      transcription: "tr",
      phonetic_us: "us",
      translation_uk: "uk",
      translation_ru: "ru",
      translation_pl: "pl",
      examples_json: ["one", "two"],
      entry_type: "idiom",
    })).toEqual({
      word: "word",
      entry_type: "idiom",
      transcription: "tr",
      phonetic_us: "us",
      translation_uk: "uk",
      translation_ru: "ru",
      translation_pl: "pl",
      examples_text: "one\ntwo",
    });

    expect(buildDictionaryEntryForm({
      translations: { uk: "nested uk", ru: "nested ru", pl: "nested pl" },
      examples_json: "already text",
    }, {
      word: "fallback",
      transcription: "fallback tr",
      phonetic_us: "fallback us",
      entry_type: "phrase_pattern",
    })).toEqual({
      word: "fallback",
      entry_type: "phrase_pattern",
      transcription: "fallback tr",
      phonetic_us: "fallback us",
      translation_uk: "nested uk",
      translation_ru: "nested ru",
      translation_pl: "nested pl",
      examples_text: "already text",
    });
  });

  it("falls back to empty form values for unsupported field shapes", () => {
    expect(buildDictionaryEntryForm(null, { word: "fallback" })).toEqual({
      word: "fallback",
      entry_type: "word",
      transcription: "",
      phonetic_us: "",
      translation_uk: "",
      translation_ru: "",
      translation_pl: "",
      examples_text: "",
    });

    expect(buildDictionaryEntryForm({
      word: 7,
      translations: "bad",
      examples_json: { one: "two" },
    })).toEqual({
      word: "",
      entry_type: "word",
      transcription: "",
      phonetic_us: "",
      translation_uk: "",
      translation_ru: "",
      translation_pl: "",
      examples_text: "",
    });
  });

  it("builds patch payloads and keeps optional fields only when supported by detail", () => {
    expect(buildDictionaryEntryPayload(baseForm, { transcription: null, phonetic_us: "" })).toEqual({
      word: "take off",
      entry_type: "phrasal_verb",
      translation_uk: "злітати",
      translation_ru: "взлетать",
      translation_pl: "startowac",
      examples_json: ["first example", "second example"],
      transcription: "tr",
      phonetic_us: "us",
    });

    expect(buildDictionaryEntryPayload(baseForm, {})).toEqual({
      word: "take off",
      entry_type: "phrasal_verb",
      translation_uk: "злітати",
      translation_ru: "взлетать",
      translation_pl: "startowac",
      examples_json: ["first example", "second example"],
    });
  });

  it("merges saved list entries with server values taking precedence", () => {
    expect(buildSavedDictionaryListEntry(
      { id: 1, word: "old", keep: true },
      { id: 2, detail: true },
      baseForm,
      {
        id: 3,
        word: "server",
        transcription: "server tr",
        phonetic_us: "server us",
        translation_uk: "server uk",
        translation_ru: "server ru",
        translation_pl: "server pl",
        translations_multiline: "server translations",
        examples_json: ["server example"],
        entry_type: "idiom",
      }
    )).toEqual({
      id: 3,
      word: "server",
      entry_type: "idiom",
      keep: true,
      detail: true,
      transcription: "server tr",
      phonetic_us: "server us",
      translation_uk: "server uk",
      translation_ru: "server ru",
      translation_pl: "server pl",
      translations_multiline: "server translations",
      examples_json: ["server example"],
    });
  });

  it("fills saved list entries from form values when the response is sparse", () => {
    expect(buildSavedDictionaryListEntry({ id: 1 }, { id: 2 }, baseForm, {})).toEqual({
      id: 2,
      word: "take off",
      entry_type: "phrasal_verb",
      transcription: " tr ",
      phonetic_us: " us ",
      translation_uk: "злітати",
      translation_ru: "взлетать",
      translation_pl: "startowac",
      translations_multiline: "uk: злітати\nru: взлетать\npl: startowac",
      examples_json: ["first example", "second example"],
    });

    expect(buildSavedDictionaryListEntry({ id: 1 }, null, baseForm, { id: 0 })).toEqual(expect.objectContaining({ id: 1 }));
  });

  it("normalizes examples text", () => {
    expect(normalizeExamplesText(["one", "two"])).toBe("one\ntwo");
    expect(normalizeExamplesText("one\ntwo")).toBe("one\ntwo");
    expect(normalizeExamplesText(undefined)).toBe("");
  });

  it("formats translations into a multiline preview", () => {
    expect(formatTranslationsMultiline(baseForm)).toBe("uk: злітати\nru: взлетать\npl: startowac");
    expect(formatTranslationsMultiline({ ...baseForm, translation_ru: "", translation_pl: "" })).toBe("uk: злітати");
    expect(formatTranslationsMultiline({ ...baseForm, translation_uk: "", translation_ru: "", translation_pl: "" })).toBe("");
  });

  it("checks field presence on primary and fallback records", () => {
    expect(hasDictionaryField({ transcription: undefined }, {}, "transcription")).toBe(true);
    expect(hasDictionaryField({}, { phonetic_us: "" }, "phonetic_us")).toBe(true);
    expect(hasDictionaryField(null, { phonetic_us: "" }, "phonetic_us")).toBe(true);
    expect(hasDictionaryField({}, null, "phonetic_us")).toBe(false);
    expect(hasDictionaryField(null, null, "phonetic_us")).toBe(false);
    expect(hasDictionaryField({}, {}, "phonetic_us")).toBe(false);
  });
});
