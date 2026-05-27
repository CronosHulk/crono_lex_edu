import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const projectDir = dirname(scriptDir);
const distDir = join(projectDir, "dist");
const indexPath = join(distDir, "index.html");

function sriFor(content) {
  return `sha384-${createHash("sha384").update(content).digest("base64")}`;
}

async function integrityForAsset(src) {
  const normalizedSrc = src.replace(/^\/admin\//, "").replace(/^\//, "");
  const content = await readFile(join(distDir, normalizedSrc));
  return sriFor(content);
}

function stripSriAttributes(tag) {
  return tag
    .replace(/\s+integrity="[^"]*"/g, "")
    .replace(/\s+crossorigin(?:="[^"]*")?/g, "");
}

async function addScriptIntegrity(html) {
  const assetTagPattern =
    /<(script|link)\b(?=[^>]*(?:\bsrc|\bhref)="([^"]+)")[^>]*(?:><\/script>|>)/g;
  const assetTags = [...html.matchAll(assetTagPattern)].filter(([tag, tagName]) => {
    if (tagName === "script") {
      return true;
    }
    return /\brel="(?:modulepreload|stylesheet)"/.test(tag);
  });
  const replacements = await Promise.all(
    assetTags.map(async ([tag, tagName, src]) => {
      const integrity = await integrityForAsset(src);
      const cleanTag = stripSriAttributes(tag);
      const suffix = tagName === "script" ? "></script>" : ">";
      return {
        tag,
        replacement: cleanTag.replace(
          suffix,
          ` integrity="${integrity}" crossorigin="anonymous"${suffix}`,
        ),
      };
    }),
  );

  return replacements.reduce(
    (updatedHtml, { tag, replacement }) => updatedHtml.replace(tag, replacement),
    html,
  );
}

const indexHtml = await readFile(indexPath, "utf8");
await writeFile(indexPath, await addScriptIntegrity(indexHtml));
