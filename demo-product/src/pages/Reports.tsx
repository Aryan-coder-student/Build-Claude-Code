import { useState } from "react";
import { Button, Card, Field, Page, Table } from "../ui";

const REPORTS = [
  ["Weekly Retention", "Retention", "Maya", "Yesterday"],
  ["Signup Funnel", "Funnel", "Jordan", "3 days ago"],
  ["Feature Adoption Q3", "Adoption", "Sam", "1 week ago"],
];

export default function Reports() {
  const [creating, setCreating] = useState(false);
  return (
    <Page
      title="Reports"
      subtitle="Create, schedule, and share analytics reports on retention, funnels, and adoption."
      actions={<Button testId="create-report" onClick={() => setCreating(true)}>New Report</Button>}
    >
      {creating && (
        <Card>
          <h2 className="font-medium">Create report</h2>
          <form className="mt-4 grid max-w-lg gap-4" onSubmit={(e) => { e.preventDefault(); setCreating(false); }}>
            <Field label="Report name" testId="report-name" placeholder="e.g. Monthly Retention" />
            <Field label="Report type" testId="report-type" options={["Retention", "Funnel", "Adoption", "Revenue"]} />
            <Field label="Date range" testId="report-range" options={["Last 7 days", "Last 30 days", "Last quarter"]} />
            <div className="flex gap-2">
              <Button type="submit" testId="save-report">Create report</Button>
              <Button variant="secondary" testId="cancel-report" onClick={() => setCreating(false)}>Cancel</Button>
            </div>
          </form>
        </Card>
      )}
      <Table
        head={["Report", "Type", "Owner", "Updated", ""]}
        rows={REPORTS.map((r, i) => [...r, <Button key={i} variant="ghost" testId={i === 0 ? "share-report" : undefined}>Share</Button>])}
      />
    </Page>
  );
}
