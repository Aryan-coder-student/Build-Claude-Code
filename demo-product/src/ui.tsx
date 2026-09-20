import type { ReactNode } from "react";
import { useEffect } from "react";

export function Page({ title, subtitle, children, actions }: { title: string; subtitle?: string; children: ReactNode; actions?: ReactNode }) {
  useEffect(() => {
    document.title = `${title} — Lumen`;
  }, [title]);
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
        </div>
        {actions && <div className="flex gap-2">{actions}</div>}
      </div>
      {children}
    </div>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>{children}</div>;
}

export function Button({ children, variant = "primary", testId, onClick, type = "button" }: { children: ReactNode; variant?: "primary" | "secondary" | "ghost"; testId?: string; onClick?: () => void; type?: "button" | "submit" }) {
  const styles = {
    primary: "bg-indigo-600 text-white hover:bg-indigo-700",
    secondary: "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50",
    ghost: "text-indigo-600 hover:bg-indigo-50",
  }[variant];
  return (
    <button type={type} data-testid={testId} onClick={onClick} className={`rounded-lg px-4 py-2 text-sm font-medium transition ${styles}`}>
      {children}
    </button>
  );
}

export function Field({ label, testId, type = "text", placeholder, options }: { label: string; testId: string; type?: string; placeholder?: string; options?: string[] }) {
  const cls = "mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200";
  return (
    <label className="block text-sm font-medium text-slate-700">
      {label}
      {options ? (
        <select data-testid={testId} name={testId} className={cls} defaultValue={options[0]}>
          {options.map((o) => <option key={o}>{o}</option>)}
        </select>
      ) : (
        <input data-testid={testId} name={testId} type={type} placeholder={placeholder} className={cls} />
      )}
    </label>
  );
}

export function Stat({ label, value, delta }: { label: string; value: string; delta?: string }) {
  return (
    <Card>
      <div className="text-sm text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
      {delta && <div className="mt-1 text-xs text-emerald-600">{delta}</div>}
    </Card>
  );
}

export function Table({ head, rows }: { head: string[]; rows: ReactNode[][] }) {
  return (
    <Card className="overflow-hidden p-0">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
          <tr>{head.map((h) => <th key={h} className="px-5 py-3 font-medium">{h}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((r, i) => (
            <tr key={i} className="hover:bg-slate-50">{r.map((c, j) => <td key={j} className="px-5 py-3">{c}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}
