import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // The backend proxy target, overridable via VITE_API_TARGET (e.g. if the
  // default port is taken or the backend runs elsewhere). Defaults to the
  // FastAPI dev port.
  const env = loadEnv(mode, process.cwd(), '');
  const apiTarget = env.VITE_API_TARGET || 'http://localhost:8420';

  return {
    plugins: [react()],
    server: {
      // Bind all interfaces (0.0.0.0), not just container-localhost, so the
      // dev server is reachable through the dev container's forwarded port.
      host: true,
      port: 5173,
      // Fail loudly if 5173 is taken instead of silently hopping to 5174
      // (which would break port forwarding and the API proxy expectation).
      strictPort: true,
      proxy: {
        // Proxy API calls to the FastAPI backend during dev.
        '/simulation': apiTarget,
        '/health': apiTarget,
      },
    },
  };
});
