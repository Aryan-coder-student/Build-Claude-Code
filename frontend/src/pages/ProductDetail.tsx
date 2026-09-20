import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { API_URL, api, type Feature, type Job, type Knowledge, type Product } from "../api";
import { Card, StageList, StatusBadge } from "../components";

type Tab = "features" | "knowledge" | "demos";

// Injects widget.js into whatever page the user is on (same thing the snippet does, without editing the product's HTML).
const bookmarklet = (p: Product) =>
  `javascript:(function(){if(window.__demoAgentLoaded)return;var s=document.createElement('script');s.src='${API_URL}/widget.js';s.setAttribute('data-product-id','${p.id}');document.body.appendChild(s);})();`;

export default function ProductDetail() {
  const { id = "" } = useParams();
  const [product, setProduct] = useState<Product | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [knowledge, setKnowledge] = useState<Knowledge | null>(null);
  const [tab, setTab] = useState<Tab>("features");
  const [selected, setSelected] = useState<Feature | null>(null);

  useEffect(() => {
    let active = true;
    const tick = async () => {
      const [p, j] = await Promise.all([api.getProduct(id), api.getJob(id)]);
      if (!active) return;
      setProduct(p); setJob(j);
      if (p.status === "READY" || p.counts.features > 0) api.getKnowledge(id).then((k) => active && setKnowledge(k));
    };
    tick();
    const t = setInterval(tick, 1500);
    return () => { active = false; clearInterval(t); };
  }, [id]);

  if (!product) return <p className="text-sm text-slate-500">Loading…</p>;
  const flowFor = (f: Feature) => knowledge?.demo_flows.find((d) => d.feature_id === f.id);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{product.name}</h1>
          <p className="text-sm text-slate-500">{product.url} · <code className="text-xs">{product.id}</code></p>
          {product.description && <p className="mt-2 max-w-2xl text-sm text-slate-700">{product.description}</p>}
        </div>
        <div className="flex items-center gap-3">
          <a href={product.url} target="_blank" rel="noreferrer" className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700">Open product with assistant ↗</a>
          <StatusBadge status={product.status} />
          <button onClick={() => api.reindex(id).then(setJob)} className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-50">Re-index</button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <StageList job={job} productName={product.name} />
        <Card title="Knowledge base" className="col-span-2">
          <div className="grid grid-cols-4 gap-3">
            {(["pages", "features", "questions", "demo_flows"] as const).map((k) => (
              <div key={k} className="rounded-lg bg-slate-50 p-4"><div className="text-xs uppercase tracking-wide text-slate-500">{k.replace("_", " ")}</div><div className="mt-1 text-2xl font-semibold">{product.counts[k]}</div></div>
            ))}
          </div>
          <div className="mt-4 rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
            <div className="mb-1 text-slate-400">Widget snippet</div>
            <code className="break-all">{product.snippet}</code>
          </div>
          <div className="mt-3 flex items-center justify-between rounded-lg border border-dashed border-slate-300 p-3 text-xs text-slate-600">
            <span>No snippet installed yet? Drag this to your bookmarks bar and click it on any page of the product to add the assistant.</span>
            <a ref={(el) => el?.setAttribute("href", bookmarklet(product))} className="ml-3 shrink-0 rounded-md bg-slate-100 px-2 py-1 font-medium text-slate-700 hover:bg-slate-200">✦ {product.name} Assistant</a>
          </div>
        </Card>
      </div>

      <div className="flex gap-2 border-b border-slate-200">
        {(["features", "knowledge", "demos"] as Tab[]).map((t) => (
          <button key={t} onClick={() => setTab(t)} className={`-mb-px border-b-2 px-4 py-2 text-sm capitalize ${tab === t ? "border-indigo-600 font-medium text-indigo-700" : "border-transparent text-slate-500 hover:text-slate-700"}`}>{t === "demos" ? "Demo flows" : t}</button>
        ))}
      </div>

      {!knowledge && <p className="text-sm text-slate-500">Knowledge will appear here once indexing completes.</p>}

      {knowledge && tab === "features" && (
        <div className="grid grid-cols-3 gap-6">
          <Card title={`Features (${knowledge.features.length})`}>
            <ul className="divide-y divide-slate-100">
              {knowledge.features.map((f) => (
                <li key={f.id}>
                  <button onClick={() => setSelected(f)} className={`flex w-full items-center justify-between px-1 py-2 text-left text-sm hover:text-indigo-700 ${selected?.id === f.id ? "font-medium text-indigo-700" : ""}`}>
                    <span>{f.name}</span>
                    <span className={`rounded px-1.5 py-0.5 text-[10px] uppercase ${f.kind === "action" ? "bg-violet-100 text-violet-700" : "bg-slate-100 text-slate-600"}`}>{f.kind}</span>
                  </button>
                </li>
              ))}
            </ul>
          </Card>
          <Card className="col-span-2" title={selected ? selected.name : "Select a feature"}>
            {selected ? (
              <div className="space-y-4 text-sm">
                <p className="text-slate-700">{selected.description}</p>
                <Row label="Route"><code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">{selected.route}</code></Row>
                <Row label="Navigation path">{selected.nav_path.join(" › ")}</Row>
                <Row label="Elements">
                  <ul className="space-y-1">{selected.elements.slice(0, 8).map((e) => <li key={e.selector}><span className="text-slate-700">{e.name}</span> <code className="ml-1 rounded bg-slate-100 px-1 py-0.5 text-[11px]">{e.selector}</code> <span className="text-xs text-slate-400">{e.role}</span></li>)}</ul>
                </Row>
                <Row label="Questions"><ul className="list-disc pl-4 text-slate-600">{selected.questions.slice(0, 5).map((q) => <li key={q}>{q}</li>)}</ul></Row>
                <Row label="Demo steps"><Steps steps={flowFor(selected)?.steps ?? []} /></Row>
              </div>
            ) : <p className="text-sm text-slate-500">Pick a feature on the left to see its route, navigation path, elements, and demo steps.</p>}
          </Card>
        </div>
      )}

      {knowledge && tab === "knowledge" && (
        <div className="grid grid-cols-2 gap-6">
          <Card title={`Pages (${knowledge.pages.length})`}>
            <ul className="divide-y divide-slate-100 text-sm">{knowledge.pages.map((p) => <li key={p.id} className="flex justify-between py-2"><span>{p.title}</span><code className="text-xs text-slate-500">{p.path} · {p.element_count} elements</code></li>)}</ul>
          </Card>
          <Card title={`Questions & answers (${knowledge.qna.length})`}>
            <ul className="max-h-[520px] space-y-3 overflow-y-auto text-sm">{knowledge.qna.map((q) => <li key={q.id}><div className="font-medium">{q.question}</div><div className="text-slate-600">{q.answer}</div></li>)}</ul>
          </Card>
        </div>
      )}

      {knowledge && tab === "demos" && (
        <div className="grid grid-cols-2 gap-6">
          {knowledge.demo_flows.map((d) => (
            <Card key={d.id} title={d.name}><p className="mb-3 text-sm text-slate-600">{d.description}</p><Steps steps={d.steps} /></Card>
          ))}
        </div>
      )}
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><div className="text-xs uppercase tracking-wide text-slate-500">{label}</div><div className="mt-1">{children}</div></div>;
}

function Steps({ steps }: { steps: { type: string; selector?: string; path?: string; value?: string; message?: string }[] }) {
  if (!steps.length) return <span className="text-slate-400">No demo flow.</span>;
  return (
    <ol className="space-y-1 text-sm">
      {steps.map((s, i) => (
        <li key={i} className="flex gap-2">
          <span className="w-5 text-slate-400">{i + 1}.</span>
          <span className="w-20 rounded bg-indigo-50 px-1.5 text-center text-xs font-medium uppercase text-indigo-700">{s.type}</span>
          <span className="text-slate-600"><code className="text-xs">{s.path ?? s.selector ?? ""}</code>{s.value && <span className="ml-1 text-xs">= "{s.value}"</span>}{s.message && <span className="ml-1 text-slate-500">{s.message}</span>}</span>
        </li>
      ))}
    </ol>
  );
}
