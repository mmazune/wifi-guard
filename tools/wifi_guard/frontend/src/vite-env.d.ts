/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_DATA_MODE?: "api" | "hosted";
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
