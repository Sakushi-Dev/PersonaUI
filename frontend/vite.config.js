import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': 'http://localhost:5000',
      '/chat': 'http://localhost:5000',
      '/chat_stream': 'http://localhost:5000',
      '/afterthought': 'http://localhost:5000',
      '/static/images': 'http://localhost:5000',
      '/get_char_config': 'http://localhost:5000',
      '/get_available_options': 'http://localhost:5000',
      '/save_char_config': 'http://localhost:5000',
      '/clear_chat': 'http://localhost:5000',
    },
  },
  build: {
    outDir: 'dist',
  },
});
