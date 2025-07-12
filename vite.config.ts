import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

export default defineConfig({
  base: "/",              // keep leading‑slash imports working
  server: { host: "::", port: 8080 },
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "/src": path.resolve(__dirname, "./src")   // ← add this line
    },
  },
});
