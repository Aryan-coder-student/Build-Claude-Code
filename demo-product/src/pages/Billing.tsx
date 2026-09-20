import { Button, Card, Page, Table } from "../ui";

const PLANS = [
  { name: "Starter", price: "$0", desc: "Up to 10k events/month, 2 seats." },
  { name: "Growth", price: "$99", desc: "1M events/month, 10 seats, scheduled reports.", current: true },
  { name: "Scale", price: "$399", desc: "Unlimited events, SSO, priority support." },
];

export default function Billing() {
  return (
    <Page title="Billing" subtitle="Manage your subscription plan, payment method, and invoices.">
      <div className="grid grid-cols-3 gap-4">
        {PLANS.map((p) => (
          <Card key={p.name} className={p.current ? "border-indigo-400 ring-2 ring-indigo-100" : ""}>
            <div className="flex items-baseline justify-between">
              <h2 className="font-medium">{p.name}</h2>
              <span className="text-lg font-semibold">{p.price}<span className="text-xs text-slate-500">/mo</span></span>
            </div>
            <p className="mt-2 text-sm text-slate-500">{p.desc}</p>
            <div className="mt-4">
              {p.current ? <span className="text-xs font-medium text-indigo-700">Current plan</span> : <Button variant="secondary" testId={p.name === "Scale" ? "upgrade-plan" : undefined}>Choose {p.name}</Button>}
            </div>
          </Card>
        ))}
      </div>
      <Card className="flex items-center justify-between">
        <div>
          <h2 className="font-medium">Payment method</h2>
          <p className="mt-1 text-sm text-slate-500">Visa ending in 4242 · expires 08/28</p>
        </div>
        <Button variant="secondary" testId="manage-payment">Manage payment method</Button>
      </Card>
      <Table head={["Invoice", "Date", "Amount", "Status"]} rows={[["INV-0042", "Sep 1, 2026", "$99.00", "Paid"], ["INV-0041", "Aug 1, 2026", "$99.00", "Paid"]]} />
    </Page>
  );
}
