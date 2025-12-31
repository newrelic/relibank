import { reactRouter } from "@react-router/dev/vite";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig(({ mode }: { mode: string }) => ({
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
    },
    allowedHosts: ['relibank.westus2.cloudapp.azure.com'],
    // Only use proxy in development mode (local machine)
    // In production, the ingress handles routing to backend services
    ...(mode === 'development' && {
      proxy: {
        '/chatbot-service': {
          target: 'http://chatbot-service:5003',
          changeOrigin: true
        },
        '/bill-pay-service': {
          target: 'http://bill-pay-service:5000',
          changeOrigin: true
        }
      }
    })
  },
}));
