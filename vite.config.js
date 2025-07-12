import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
<<<<<<< HEAD
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
  },
  plugins: [
    react(),
    mode === 'development' &&
    componentTagger(),
  ].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));
=======

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

>>>>>>> 84bfba8ba7c78b70c185f607f2dcac9445fef8e7
