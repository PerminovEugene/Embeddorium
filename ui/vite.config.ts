import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
// import autoprefixer from "autoprefixer";
import tailwindcss from "@tailwindcss/vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // UI_PORT keeps the dev server, the compose port mapping and the server's
    // CORS allowlist on one value. Set in .env / .env.docker; defaults to 5173.
    port: Number(process.env.UI_PORT) || 5173,
  },
  // css: {
  //   postcss: {
  //     plugins: [autoprefixer],
  //   },
  // },
});
