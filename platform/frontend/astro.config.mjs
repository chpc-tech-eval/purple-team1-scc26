// Static build served by the API. The API sends CSP default-src 'self', so
// nothing may be inlined: scripts and styles are emitted as files.
import { defineConfig } from "astro/config";

export default defineConfig({
  output: "static",
  build: { inlineStylesheets: "never" },
  vite: { build: { assetsInlineLimit: 0 } },
});
