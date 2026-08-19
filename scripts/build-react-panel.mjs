import { readdir, readFile, rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { gzipSync } from "node:zlib";
import { build } from "vite";

const root = resolve(import.meta.dirname, "..");
const outputDir = resolve(root, ".tmp-react-panel-build");
const assetDir = resolve(root, "python-package/teledrive/react_panel_assets");

async function findOutput(extension) {
  const names = await readdir(outputDir);
  const matches = names.filter((name) => name.endsWith(extension));
  if (matches.length !== 1) {
    throw new Error(
      `Expected one ${extension} panel output, found: ${matches.join(", ") || "none"}`,
    );
  }
  return resolve(outputDir, matches[0]);
}

try {
  await build({
    root,
    configFile: false,
    logLevel: "warn",
    build: {
      emptyOutDir: true,
      lib: {
        entry: resolve(root, "src/components/teleDrive/gradioEntry.tsx"),
        formats: ["iife"],
        name: "TeleDriveGradioPanel",
        fileName: () => "panel.bundle.js",
      },
      minify: "oxc",
      outDir: outputDir,
      sourcemap: false,
      target: "es2020",
    },
  });

  const [bundle, css] = await Promise.all([
    readFile(await findOutput(".js")),
    readFile(await findOutput(".css")),
  ]);
  await Promise.all([
    writeFile(resolve(assetDir, "panel.bundle.gz"), gzipSync(bundle, { mtime: 0 })),
    writeFile(resolve(assetDir, "panel.css.gz"), gzipSync(css, { mtime: 0 })),
  ]);
  console.log(`react panel rebuilt: ${bundle.length} JS bytes, ${css.length} CSS bytes`);
} finally {
  await rm(outputDir, { recursive: true, force: true });
}
