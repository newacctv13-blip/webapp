import { defineConfig } from 'vite';
import { readFileSync, writeFileSync, copyFileSync, existsSync, mkdirSync } from 'fs';
import { resolve, dirname } from 'path';

export default defineConfig({
  base: './',
  build: {
    cssMinify: true,
    rollupOptions: {
      output: {
        format: 'iife',
        inlineDynamicImports: true,
      },
    },
  },
  plugins: [
    {
      name: 'fix-html-output',
      closeBundle() {
        const dist = resolve(__dirname, 'dist');
        const html = readFileSync(resolve(dist, 'index.html'), 'utf-8');
        const result = html
          .replace(
            /<script type="module" crossorigin src="([^"]+)"><\/script>/g,
            '<script defer src="$1"></script>'
          )
          .replace(
            /<link rel="stylesheet" crossorigin href="([^"]+)">/g,
            '<link rel="stylesheet" href="$1">'
          );
        writeFileSync(resolve(dist, 'index.html'), result, 'utf-8');
        copyFileSync(resolve(__dirname, 'data.json'), resolve(dist, 'data.json'));
        copyFileSync(resolve(__dirname, 'visit.html'), resolve(dist, 'visit.html'));
        const cssSrc = resolve(__dirname, 'css', 'style.css');
        const cssDst = resolve(dist, 'css', 'style.css');
        if (existsSync(cssSrc)) {
          mkdirSync(resolve(dist, 'css'), { recursive: true });
          copyFileSync(cssSrc, cssDst);
        }
      },
    },
  ],
});
