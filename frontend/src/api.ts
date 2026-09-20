export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
export const TENANT_ID = import.meta.env.VITE_TENANT_ID ?? "ten_demo";

export type LoginConfig = { url: string; username: string; password: string; username_selector: string; password_selector: string; submit_selector: string };
export type Product = {
  id: string; tenant_id: string; name: string; url: string; description: string; status: string; requires_login: boolean;
  counts: { pages: number; features: number; questions: number; demo_flows: number }; snippet: string;
};
export type Job = { id: string; status: string; stage: string; progress: number; message: string; stats: Record<string, number>; updated_at: string };
export type Element = { name: string; selector: string; role: string };
export type Feature = { id: string; name: string; slug: string; kind: "page" | "action"; description: string; route: string; nav_path: string[]; elements: Element[]; questions: string[] };
export type Step = { type: string; selector?: string; path?: string; value?: string; message?: string; ms?: number; label?: string };
export type DemoFlow = { id: string; feature_id: string; name: string; description: string; steps: Step[] };
export type Knowledge = {
  pages: { id: string; path: string; title: string; headings: string[]; element_count: number; links: string[] }[];
  features: Feature[];
  navigation: { from: string; to: string; selector: string; label: string }[];
  qna: { id: string; feature_id: string; question: string; answer: string }[];
  demo_flows: DemoFlow[];
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { ...init, headers: { "content-type": "application/json", "X-Tenant-Id": TENANT_ID, ...(init?.headers ?? {}) } });
  if (!res.ok) throw new Error((await res.json().catch(() => ({ detail: res.statusText }))).detail ?? res.statusText);
  return res.json() as Promise<T>;
}

export const api = {
  listProducts: () => request<Product[]>("/api/products"),
  createProduct: (body: { name: string; url: string; id?: string; login?: LoginConfig }) => request<Product>("/api/products", { method: "POST", body: JSON.stringify(body) }),
  getProduct: (id: string) => request<Product>(`/api/products/${id}`),
  getJob: (id: string) => request<Job | null>(`/api/products/${id}/job`),
  getKnowledge: (id: string) => request<Knowledge>(`/api/products/${id}/knowledge`),
  reindex: (id: string) => request<Job>(`/api/products/${id}/reindex`, { method: "POST" }),
};

export const STAGES = [
  ["DISCOVERING_PAGES", "Discovering pages"],
  ["EXTRACTING_FEATURES", "Extracting features"],
  ["BUILDING_NAVIGATION", "Building navigation graph"],
  ["GENERATING_QA", "Generating questions"],
  ["GENERATING_DEMOS", "Creating demo flows"],
  ["INDEXING_KNOWLEDGE", "Building knowledge index"],
] as const;
