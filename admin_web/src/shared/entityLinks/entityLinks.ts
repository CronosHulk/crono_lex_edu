export type EntityLinkType = "user" | "import_job" | "task_log" | "dictionary_entry" | "user_dictionary_entry";

export type EntityLink = {
  type: EntityLinkType;
  id: string | number;
};

export type ExtractEntityLinksOptions = {
  taskType?: string | null;
};

const MAX_LINKS = 20;
const MAX_DEPTH = 5;

const singularKeyToType: Record<string, EntityLinkType> = {
  user_id: "user",
  user_uuid: "user",
  actor_user_id: "user",
  actor_user_uuid: "user",
  created_by_user_uuid: "user",
  import_job_id: "import_job",
  created_import_job_id: "import_job",
  task_log_id: "task_log",
  dictionary_entry_id: "dictionary_entry",
  existing_word_id: "dictionary_entry",
  word_id: "dictionary_entry",
  user_dictionary_entry_id: "user_dictionary_entry"
};

const pluralKeyToType: Record<string, EntityLinkType> = {
  user_ids: "user",
  user_uuids: "user",
  import_job_ids: "import_job",
  task_log_ids: "task_log",
  dictionary_entry_ids: "dictionary_entry",
  existing_word_ids: "dictionary_entry",
  word_ids: "dictionary_entry",
  user_dictionary_entry_ids: "user_dictionary_entry"
};

export function extractEntityLinks(value: unknown, { taskType: _taskType }: ExtractEntityLinksOptions = {}): EntityLink[] {
  const links: EntityLink[] = [];
  const seen = new Set<string>();

  function add(type: EntityLinkType, rawId: unknown) {
    const id = normalizeEntityId(rawId);
    if (id === null) return;
    const key = `${type}-${id}`;
    if (seen.has(key)) return;
    seen.add(key);
    links.push({ type, id });
  }

  function walk(node: unknown, depth = 0) {
    if (!node || depth > MAX_DEPTH) return;
    if (Array.isArray(node)) {
      node.forEach((item) => walk(item, depth + 1));
      return;
    }
    if (!isRecord(node)) return;

    Object.entries(node).forEach(([key, raw]) => {
      const normalizedKey = key.toLowerCase();
      const singularType = singularKeyToType[normalizedKey];
      const pluralType = pluralKeyToType[normalizedKey];

      if (singularType) {
        add(singularType, raw);
      } else if (pluralType && Array.isArray(raw)) {
        raw.forEach((item) => add(pluralType, item));
      }

      walk(raw, depth + 1);
    });
  }

  walk(value);
  return links.slice(0, MAX_LINKS);
}

export function normalizeEntityId(value: unknown): string | number | null {
  if (typeof value === "number" && Number.isSafeInteger(value) && value > 0) return value;
  if (typeof value !== "string") return null;

  const trimmed = value.trim();
  if (/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(trimmed)) {
    return trimmed;
  }
  if (!/^\d+$/.test(trimmed)) return null;

  const parsed = Number(trimmed);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
