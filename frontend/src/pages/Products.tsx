import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, type LoginConfig, type Product } from "../api";
import { StatusBadge } from "../components";

const slugify = (s: string) => "prod_" + (s.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "") || "product");

export default function Products() {
  const [products, setProducts] = useState<Product[]>([]);
  const [name, setName] = useState("Demo SaaS");
  const [url, setUrl] = useState("http://localhost:3000");
  const [id, setId] = useState(slugify("Demo SaaS"));
  const [idTouched, setIdTouched] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState<Product | null>(null);
  const [needsLogin, setNeedsLogin] = useState(false);
  const [login, setLogin] = useState<LoginConfig>({ url: "", username: "", password: "", username_selector: "input[name='username']", password_selector: "input[name='password']", submit_selector: "button[type='submit']" });
  const setLoginField = (k: keyof LoginConfig) => (e: React.ChangeEvent<HTMLInputElement>) => setLogin({ ...login, [k]: e.target.value });

  const refresh = () => api.listProducts().then(setProducts).catch((e) => setError(e.message));
  useEffect(() => { refresh(); const t = setInterval(refresh, 3000); return () => clearInterval(t); }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const p = await api.createProduct({ name, url, id, login: needsLogin ? { ...login, url: login.url || url } : undefined });
      setCreated(p);
      refresh();
    } catch (err) { setError((err as Error).message); }
  };

  return (
    <div className="grid grid-cols-3 gap-6">
      <section className="col-span-2 space-y-4">
        <h1 className="text-2xl font-semibold tracking-tight">Products</h1>
        {products.length === 0 && <p className="text-sm text-slate-500">No products yet. Register one to start indexing.</p>}
        {products.map((p) => (
          <Link key={p.id} to={`/products/${p.id}`} className="block rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-indigo-300">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">{p.name}</div>
                <div className="text-xs text-slate-500">{p.url} · {p.id}{p.requires_login && " · login configured"}</div>
              </div>
              <StatusBadge status={p.status} />
            </div>
            <div className="mt-3 grid grid-cols-4 gap-2 text-sm">
              {(["pages", "features", "questions", "demo_flows"] as const).map((k) => (
                <div key={k} className="rounded-lg bg-slate-50 px-3 py-2"><div className="text-xs text-slate-500">{k.replace("_", " ")}</div><div className="font-semibold">{p.counts[k]}</div></div>
              ))}
            </div>
          </Link>
        ))}
      </section>
      <aside className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="font-medium">Register a product</h2>
        <p className="mt-1 text-xs text-slate-500">We'll crawl it, learn its features, and generate Q&A and interactive demos automatically.</p>
        <form className="mt-4 space-y-3" onSubmit={submit}>
          <label className="block text-sm">Product name
            <input className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" value={name} onChange={(e) => { setName(e.target.value); if (!idTouched) setId(slugify(e.target.value)); }} required />
          </label>
          <label className="block text-sm">URL
            <input className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" value={url} onChange={(e) => setUrl(e.target.value)} required />
          </label>
          <label className="block text-sm">Product ID <span className="text-xs text-slate-400">(used in the widget snippet)</span>
            <input className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs" value={id} onChange={(e) => { setId(e.target.value); setIdTouched(true); }} required />
          </label>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={needsLogin} onChange={(e) => setNeedsLogin(e.target.checked)} /> Product requires login</label>
          {needsLogin && (
            <div className="space-y-2 rounded-lg bg-slate-50 p-3">
              {([["url", "Login page URL (defaults to product URL)"], ["username", "Username"], ["password", "Password"], ["username_selector", "Username field selector"], ["password_selector", "Password field selector"], ["submit_selector", "Submit button selector"]] as [keyof LoginConfig, string][]).map(([k, label]) => (
                <label key={k} className="block text-xs text-slate-600">{label}
                  <input className="mt-0.5 w-full rounded-md border border-slate-300 px-2 py-1 font-mono text-xs" type={k === "password" ? "password" : "text"} value={login[k]} onChange={setLoginField(k)} />
                </label>
              ))}
            </div>
          )}
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button className="w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">Register & start indexing</button>
        </form>
        {created && (
          <div className="mt-4 rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
            <div className="mb-1 text-slate-400">Add this to the product's HTML:</div>
            <code className="break-all">{created.snippet}</code>
          </div>
        )}
      </aside>
    </div>
  );
}
