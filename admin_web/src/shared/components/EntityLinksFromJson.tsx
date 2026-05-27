import { Button, Chip, Stack } from "@mui/material";
import { ExternalLink } from "lucide-react";

import { extractEntityLinks } from "../entityLinks/entityLinks";
import type { EntityLink } from "../entityLinks/entityLinks";

export type AdminRole = "super_admin" | "admin" | "admin_editor" | "student" | string;

export type EntityLinksUser = {
  acl_group_title?: AdminRole | null;
} | null | undefined;

export type EntityLinksLabels = {
  importJob?: string;
};

export type EntityLinksFromJsonProps = {
  value: unknown;
  t?: EntityLinksLabels;
  user?: EntityLinksUser;
  taskType?: string | null;
  onOpenImportJob?: (id: number) => void;
  onOpenUser?: (id: string | number) => void;
  onOpenTaskLog?: (id: number) => void;
  onOpenDictionaryEntry?: (id: number) => void;
};

export function EntityLinksFromJson({
  value,
  t,
  user,
  taskType,
  onOpenImportJob,
  onOpenUser,
  onOpenTaskLog,
  onOpenDictionaryEntry
}: EntityLinksFromJsonProps) {
  const links = extractEntityLinks(value, { taskType });
  if (links.length === 0) return null;

  const isSuperAdmin = user?.acl_group_title === "super_admin";

  return (
    <Stack className="link-row" direction="row" sx={{ flexWrap: "wrap", gap: 1 }}>
      {links.map((link) => (
        <EntityLinkControl
          key={`${link.type}-${link.id}`}
          link={link}
          isSuperAdmin={isSuperAdmin}
          importJobLabel={t?.importJob || "Import job"}
          onOpenImportJob={onOpenImportJob}
          onOpenUser={onOpenUser}
          onOpenTaskLog={onOpenTaskLog}
          onOpenDictionaryEntry={onOpenDictionaryEntry}
        />
      ))}
    </Stack>
  );
}

type EntityLinkControlProps = {
  link: EntityLink;
  isSuperAdmin: boolean;
  importJobLabel: string;
  onOpenImportJob?: (id: number) => void;
  onOpenUser?: (id: string | number) => void;
  onOpenTaskLog?: (id: number) => void;
  onOpenDictionaryEntry?: (id: number) => void;
};

function EntityLinkControl({
  link,
  isSuperAdmin,
  importJobLabel,
  onOpenImportJob,
  onOpenUser,
  onOpenTaskLog,
  onOpenDictionaryEntry
}: EntityLinkControlProps) {
  switch (link.type) {
    case "user":
      return renderButton(`User #${link.id}`, link.id, onOpenUser);
    case "import_job":
      return renderNumberButton(`${importJobLabel} #${link.id}`, link.id, onOpenImportJob);
    case "task_log":
      return renderNumberButton(`Task #${link.id}`, link.id, onOpenTaskLog);
    case "dictionary_entry":
      return isSuperAdmin
        ? renderNumberButton(`Word #${link.id}`, link.id, onOpenDictionaryEntry)
        : renderChip(`Word #${link.id}`);
    case "user_dictionary_entry":
      return renderChip(`User word #${link.id}`);
  }
}

function renderNumberButton(label: string, id: string | number, onClick?: (id: number) => void) {
  if (typeof id !== "number") return renderChip(label);
  if (!onClick) return renderChip(label);

  return (
    <Button className="ghost compact" variant="outlined" onClick={() => onClick(id)} startIcon={<ExternalLink />}>
      {label}
    </Button>
  );
}

function renderButton(label: string, id: string | number, onClick?: (id: string | number) => void) {
  if (!onClick) return renderChip(label);

  return (
    <Button className="ghost compact" variant="outlined" onClick={() => onClick(id)} startIcon={<ExternalLink />}>
      {label}
    </Button>
  );
}

function renderChip(label: string) {
  return <Chip className="chip" label={label} size="small" variant="outlined" />;
}
