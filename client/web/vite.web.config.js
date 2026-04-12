/** vite web config 설정을 정의한다. */

import { defineConfig } from "vite";
import { resolve } from "node:path";
import react from "@vitejs/plugin-react";

export default defineConfig({
    root: __dirname,
    base: "./",
    plugins: [react()],
    resolve: {
        alias: {
            "@caps-client-shared": resolve(__dirname, "..", "shared", "src"),
        },
    },
    build: {
        outDir: resolve(__dirname, "dist", "web"),
        emptyOutDir: true,
        sourcemap: true,
        rollupOptions: {
            input: resolve(__dirname, "index.html"),
        },
    },
});
