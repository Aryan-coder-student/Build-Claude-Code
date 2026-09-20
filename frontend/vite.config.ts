import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // allow the crawler inside Docker to reach this dev server via its service name (e.g. http://demo-product:3000)
  server: { host: true, allowedHosts: true },
});
