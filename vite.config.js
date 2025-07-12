import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

export default defineConfig({
  root: ".",            // treat repo root as your project root
  base: "/",            // ensure imports beginning with “/” resolve to root
  build: {
    outDir: "dist",
    rollupOptions: {
      // explicitly point Rollup at your index.html entry
      input: path.resolve(__dirname, "index.html"),
    },
  },
  resolve: {
    alias: {
      // let you import from “@/…” to “src/…”
      "@": path.resolve(__dirname, "src"),
    },
  },
  plugins: [react()],
});

