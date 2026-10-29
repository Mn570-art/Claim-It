import { connection } from "next/server";

// Vercel injects BACKEND_URL at function runtime. It is unset during the build.
export async function serverApiUrl(path: string): Promise<string> {
  await connection();
  const bound = process.env.BACKEND_URL?.replace(/\/$/, "");
  const base = bound || process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://127.0.0.1:8741";
  const relative = path.startsWith("/") ? path.slice(1) : path;
  return new URL(relative, `${base}/`).toString();
}
