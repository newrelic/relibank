import { reactRouter } from "@react-router/dev/vite";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  plugins: [tailwindcss(), reactRouter({
    // FIX: Add historyApiFallback to ensure deep links (like /dashboard) fall back to index.html
    historyApiFallback: {
      single: true,
    }
  }), tsconfigPaths()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    // Add this to enable hot reloading
    hmr: {
      clientPort: 3000
    }
  },
});
