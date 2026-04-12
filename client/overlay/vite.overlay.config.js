import { defineConfig } from "vite";
import { resolve } from "node:path";

export default defineConfig({
    root: __dirname,
    base: "./",
    build: {
        outDir: resolve(__dirname, "dist", "overlay"),
        emptyOutDir: true,
        sourcemap: true,
        rollupOptions: {
            input: resolve(__dirname, "index.html"),
        },
    },
});
