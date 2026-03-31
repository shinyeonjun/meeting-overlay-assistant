import { defineConfig } from "vite";
import { resolve } from "node:path";

export default defineConfig({
    root: resolve(__dirname, "overlay"),
    base: "./",
    build: {
        outDir: resolve(__dirname, "dist", "overlay"),
        emptyOutDir: true,
        sourcemap: true,
        rollupOptions: {
            input: resolve(__dirname, "overlay", "index.html"),
        },
    },
});
