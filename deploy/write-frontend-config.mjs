import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

const output = resolve("mvp-app/static/config.js");
const apiBase = process.env.PARKFLOW_API_BASE || "";

mkdirSync(dirname(output), { recursive: true });
writeFileSync(
  output,
  `window.PARKFLOW_API_BASE = ${JSON.stringify(apiBase.replace(/\/$/, ""))};\n`,
  "utf8"
);

console.log(`Wrote ${output}`);
