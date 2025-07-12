import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import path from 'path'

export default defineConfig({
  base: '/',              // allow absolute imports
  server: { host: '::', port: 8080 },
  plugins: [ react() ],
  resolve: {
    alias: [
      { find: '@', replacement: path.resolve(__dirname, 'src') },
      { find: /^\/src\/(.*)$/, replacement: path.resolve(__dirname, 'src') + '/$1' }
    ]
  }
})
