import { useState } from "react";
import { Button, Card, Field, Page, Table } from "../ui";

const PROJECTS = [
  ["Web App", "Production", "812k", "2 min ago"],
  ["Mobile App", "Production", "540k", "10 min ago"],
  ["Marketing Site", "Staging", "61k", "1 hr ago"],
];

export default function Projects() {
  const [creating, setCreating] = useState(false);
  return (
    <Page
      title="Projects"
      subtitle="Projects group the events, dashboards, and reports for one product or environment."
      actions={<Button testId="create-project" onClick={() => setCreating(true)}>New Project</Button>}
    >
      {creating && (
        <Card>
          <h2 className="font-medium">Create project</h2>
          <form className="mt-4 grid max-w-lg gap-4" onSubmit={(e) => { e.preventDefault(); setCreating(false); }}>
            <Field label="Project name" testId="project-name" placeholder="e.g. Customer Portal" />
            <Field label="Environment" testId="project-environment" options={["Production", "Staging", "Development"]} />
            <div className="flex gap-2">
              <Button type="submit" testId="save-project">Create project</Button>
              <Button variant="secondary" testId="cancel-project" onClick={() => setCreating(false)}>Cancel</Button>
            </div>
          </form>
        </Card>
      )}
      <Table head={["Project", "Environment", "Events (30d)", "Last event"]} rows={PROJECTS} />
    </Page>
  );
}
