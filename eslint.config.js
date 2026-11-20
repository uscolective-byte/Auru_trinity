import eslint from "@eslint/js";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["coverage", "dist"] },
  eslint.configs.recommended,
  ...tseslint.configs.strict,
  { rules: { "@typescript-eslint/no-non-null-assertion": "off" } },
);
