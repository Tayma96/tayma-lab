import { defineConfig } from 'astro/config';
import fs from 'node:fs';

const cfg = JSON.parse(fs.readFileSync(new URL('./site.config.json', import.meta.url), 'utf-8'));

export default defineConfig({
  site: cfg.siteUrl,
  base: cfg.basePath,
  trailingSlash: 'always',
  build: { format: 'directory' },
  markdown: {
    shikiConfig: { theme: 'github-light' },
  },
});
