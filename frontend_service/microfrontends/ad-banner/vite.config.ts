import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  define: {
    'process.env.NODE_ENV': JSON.stringify('production')
  },
  build: {
    lib: {
      entry: resolve(__dirname, 'src/index.tsx'),
      name: 'RelibankAdBanner',
      formats: ['umd'],
      fileName: () => 'ad-banner.js'
    },
    rollupOptions: {
      // Externalize dependencies - expect from host
      external: ['react', 'react-dom', '@mui/material', '@emotion/react', '@emotion/styled'],
      output: {
        globals: {
          react: 'React',
          'react-dom': 'ReactDOM',
          '@mui/material': 'MaterialUI',
          '@emotion/react': 'EmotionReact',
          '@emotion/styled': 'EmotionStyled'
        },
        dir: '../../public/microfrontends/ad-banner',
        assetFileNames: '[name][extname]'
      }
    },
    outDir: '../../public/microfrontends/ad-banner',
    emptyOutDir: true
  }
});
