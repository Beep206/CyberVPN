const fs = require("fs");
const path = "/home/beep/projects/VPNBussiness/frontend/src/middleware.ts";
const original = fs.readFileSync(path, "utf8");
const fixed = original
  .replace("export default async function middleware(request: any) {", "export default async function middleware(request: NextRequest) {")
  .replace("import createMiddleware", "import { NextRequest } from \"next/server\";\nimport createMiddleware");
fs.writeFileSync(path, fixed);
console.log("DONE");
