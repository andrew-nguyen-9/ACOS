/**
 * Phase 17 — single-source build for Chrome + Firefox (ADR-019 Q7).
 *
 * Bundles the ES-module sources (which use static `import`) into classic-loadable
 * files under dist/<target>/, copies the manifest + popup, and writes the per-target
 * manifest (identical here; the gecko id already lives in the shared manifest). The
 * same source builds both — no forked Chrome/Firefox trees.
 */
import { build } from "esbuild";
import { cp, mkdir, readFile, writeFile } from "node:fs/promises";

const TARGETS = ["chrome", "firefox"];
const ENTRIES = ["src/background.js", "src/content.js", "src/popup.js"];

for (const target of TARGETS) {
  const out = `dist/${target}`;
  await mkdir(`${out}/src`, { recursive: true });
  await build({
    entryPoints: ENTRIES,
    bundle: true,
    format: "esm",
    outdir: `${out}/src`,
    target: "es2022",
    logLevel: "info",
  });
  await cp("src/popup.html", `${out}/src/popup.html`);
  const manifest = JSON.parse(await readFile("manifest.json", "utf8"));
  await writeFile(`${out}/manifest.json`, JSON.stringify(manifest, null, 2));
}
console.log("built", TARGETS.join(" + "));
