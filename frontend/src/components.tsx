import type { ReactNode } from "react";
import { STAGES, type Job } from "./api";

export function StatusBadge({ status }: { status: string }) {
  const tone = status === "READY" ? "bg-emerald-100 text-emerald-700" : status === "FAILED" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700";
  return <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${tone}`}>{status.replace(/_/g, " ")}</span>;
}

export function Card({ title, children, className = "" }: { title?: string; children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
      {title && <h2 className="mb-3 font-medium">{title}</h2>}
      {children}
    </div>
  );
}

export function StageList({ job, productName }: { job: Job | null; productName: string }) {
  const stageIndex = job ? STAGES.findIndex(([key]) => key === job.stage) : -1;
  const done = job?.status === "DONE";
  const failed = job?.status === "FAILED";
  const statLine: Record<string, (s: Record<string, number>) => string | undefined> = {
    DISCOVERING_PAGES: (s) => s.pages !== undefined ? `${s.pages} pages discovered` : undefined,
    EXTRACTING_FEATURES: (s) => s.features !== undefined ? `${s.features} features found` : undefined,
    BUILDING_NAVIGATION: (s) => s.navigation_edges !== undefined ? `${s.navigation_edges} navigation edges` : undefined,
    GENERATING_QA: (s) => s.questions !== undefined ? `${s.questions} questions` : undefined,
    GENERATING_DEMOS: (s) => s.demo_flows !== undefined ? `${s.demo_flows} demo flows` : undefined,
    INDEXING_KNOWLEDGE: (s) => s.chunks !== undefined ? `${s.chunks} knowledge chunks` : undefined,
  };
  return (
    <Card>
      <div className="flex items-center justify-between">
        <h2 className="font-medium">{done ? `${productName} is ready` : failed ? "Indexing failed" : `Analyzing ${productName}…`}</h2>
        {job && <span className="text-xs text-slate-500">{Math.round(job.progress * 100)}%</span>}
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100"><div className={`h-full transition-all ${failed ? "bg-red-500" : "bg-indigo-500"}`} style={{ width: `${(job?.progress ?? 0) * 100}%` }} /></div>
      <ul className="mt-4 space-y-2 text-sm">
        {STAGES.map(([key, label], i) => {
          const state = done || i < stageIndex ? "done" : i === stageIndex && !failed ? "active" : i === stageIndex && failed ? "failed" : "todo";
          const icon = { done: "✓", active: "→", failed: "✕", todo: "○" }[state];
          const tone = { done: "text-emerald-600", active: "text-indigo-600 font-medium", failed: "text-red-600", todo: "text-slate-400" }[state];
          const detail = job && state !== "todo" ? statLine[key]?.(job.stats) : undefined;
          return (
            <li key={key} className={`flex items-start gap-2 ${tone}`}>
              <span className="w-4">{icon}</span>
              <span>{label}{detail && <span className="ml-2 text-xs text-slate-500">{detail}</span>}</span>
            </li>
          );
        })}
      </ul>
      {job?.message && <p className={`mt-3 text-xs ${failed ? "text-red-600" : "text-slate-500"}`}>{job.message}</p>}
    </Card>
  );
}
