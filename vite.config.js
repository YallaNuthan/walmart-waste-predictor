import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

export default defineConfig({
  base: '/',        // default; ensures /src imports work
  plugins: [react()],
})
