import { Card, Page, Stat } from "../ui";

export default function Dashboard() {
  return (
    <Page title="Dashboard" subtitle="Overview of your workspace activity, usage, and recent events.">
      <div className="grid grid-cols-4 gap-4">
        <Stat label="Active projects" value="12" delta="+2 this week" />
        <Stat label="Events tracked" value="1.4M" delta="+8.1%" />
        <Stat label="Reports created" value="38" delta="+5" />
        <Stat label="Team members" value="9" />
      </div>
      <div className="grid grid-cols-3 gap-4">
        <Card className="col-span-2">
          <h2 className="font-medium">Recent activity</h2>
          <ul className="mt-3 space-y-2 text-sm text-slate-600" data-testid="recent-activity">
            <li>Maya created report <b>Weekly Retention</b></li>
            <li>Project <b>Mobile App</b> received 42k new events</li>
            <li>Jordan invited <b>sam@acme.io</b> as Analyst</li>
            <li>Billing plan upgraded to <b>Growth</b></li>
          </ul>
        </Card>
        <Card>
          <h2 className="font-medium">Quick actions</h2>
          <p className="mt-2 text-sm text-slate-500">Jump to the most common tasks: create a project, build a report, or invite a teammate.</p>
        </Card>
      </div>
    </Page>
  );
}
