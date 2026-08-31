import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  build: {
    lib: {
      entry: resolve(__dirname, "src/index.tsx"),
      formats: ["es"],
      fileName: () => "index.js",
    },
    outDir: resolve(__dirname, "../dist"),
    emptyOutDir: true,
    rollupOptions: {
      external: ["react", "react-dom"],
    },
  },
});
