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
  build: {
    // Add timestamps to bust cache on every build
    rollupOptions: {
      output: {
        entryFileNames: `assets/[name]-[hash]-${Date.now()}.js`,
        chunkFileNames: `assets/[name]-[hash]-${Date.now()}.js`,
        assetFileNames: `assets/[name]-[hash]-${Date.now()}[extname]`
      }
    }
  },
  optimizeDeps: {
    // Pre-bundle dependencies to prevent race condition on startup
    include: [
      '@mui/material',
      '@mui/icons-material',
      '@mui/icons-material/Dashboard',
      '@mui/icons-material/AccountBalanceWallet',
      '@mui/icons-material/Settings',
      '@mui/icons-material/Notifications',
      '@mui/icons-material/Business',
      '@mui/icons-material/SupportAgent',
      '@mui/icons-material/Send',
      '@mui/icons-material/Logout',
      '@mui/icons-material/Brightness4',
      '@mui/icons-material/Payment',
      '@mui/icons-material/Receipt',
      '@mui/icons-material/CreditCard',
      '@mui/icons-material/CalendarMonth',
      '@mui/icons-material/Delete',
      '@mui/icons-material/Edit',
      '@mui/icons-material/Add',
      '@mui/icons-material/AccountBalance',
      '@mui/material/styles',
      'react',
      'react-dom',
      'react-router',
      'react-router-dom',
      'recharts'
    ],
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    // Add this to enable hot reloading
    hmr: {
      clientPort: 3000
    },
    allowedHosts: ['relibank.westus2.cloudapp.azure.com', 'frontend-service.relibank.svc.cluster.local'],
    // Proxy API requests to backend services via Kubernetes service DNS
    // Backend services include the service name in their routes (e.g., /accounts-service/accounts/...)
    // so we forward the full path without rewriting
    proxy: {
      '/auth-service': {
        target: 'http://auth-service.relibank.svc.cluster.local:5002',
        changeOrigin: true
      },
      '/accounts-service': {
        target: 'http://accounts-service.relibank.svc.cluster.local:5002',
        changeOrigin: true
      },
      '/chatbot-service': {
        target: 'http://chatbot-service.relibank.svc.cluster.local:5003',
        changeOrigin: true
      },
      '/bill-pay-service': {
        target: 'http://bill-pay-service.relibank.svc.cluster.local:5000',
        changeOrigin: true
      },
      '/transaction-service': {
        target: 'http://transaction-service.relibank.svc.cluster.local:5001',
        changeOrigin: true
      }
    }
  },
}));
