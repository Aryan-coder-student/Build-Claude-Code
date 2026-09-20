import { Card, Page, Stat } from "../ui";

const BARS = [42, 55, 48, 70, 66, 82, 91];

export default function AnalyticsOverview() {
  return (
    <Page title="Analytics" subtitle="Track usage, engagement, retention, and conversion across all projects.">
      <div className="grid grid-cols-4 gap-4">
        <Stat label="Daily active users" value="8,412" delta="+4.2%" />
        <Stat label="Sessions" value="21,903" delta="+6.0%" />
        <Stat label="Retention (D7)" value="41%" delta="+1.5 pts" />
        <Stat label="Conversion" value="3.8%" />
      </div>
      <Card>
        <div className="flex items-center justify-between">
          <h2 className="font-medium">Active users, last 7 days</h2>
          <span className="text-xs text-slate-500">Updated hourly</span>
        </div>
        <div className="mt-4 flex h-40 items-end gap-3" data-testid="usage-chart">
          {BARS.map((h, i) => (
            <div key={i} className="flex-1 rounded-t-md bg-indigo-500/80" style={{ height: `${h}%` }} />
          ))}
        </div>
      </Card>
      <Card>
        <h2 className="font-medium">Reports</h2>
        <p className="mt-2 text-sm text-slate-500">Build custom reports on retention, funnels, and feature adoption in the Reports section. Reports can be scheduled and shared with your team.</p>
      </Card>
    </Page>
  );
}
