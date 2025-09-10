import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/upload': 'http://localhost:8000',
      '/recall': 'http://localhost:8000',
      '/due': 'http://localhost:8000',
      '/history': 'http://localhost:8000'
    }
  }
});
