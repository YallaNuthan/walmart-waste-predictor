import { defineConfig } from "vite"
import react from "@vitejs/plugin-react-swc"
import path from "path"
import { componentTagger } from "lovable-tagger"

export default defineConfig(({ mode }) => ({
  base: "/",  // ensure leading‑slash imports resolve
  server: {
    host: "::",
    port: 8080,
  },
  plugins: [
    react(),
    mode === "development" && componentTagger(),
  ].filter(Boolean),
  resolve: {
    alias: [
      // @ maps to src
      { find: "@", replacement: path.resolve(__dirname, "src") },
      // map /src/... to <projectRoot>/src/...
      {
        find: /^\/src\/(.*)$/,
        replacement: path.resolve(__dirname, "src") + "/$1",
      },
    ],
  },
}))
