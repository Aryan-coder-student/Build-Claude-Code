import { useState } from "react";
import { Button, Card, Field, Page } from "../ui";

export default function Invite() {
  const [sent, setSent] = useState(false);
  return (
    <Page title="Invite Member" subtitle="Send an email invitation and choose the teammate's role.">
      <Card className="max-w-lg">
        {sent ? (
          <p className="text-sm text-emerald-700" data-testid="invite-sent">Invitation sent.</p>
        ) : (
          <form className="grid gap-4" onSubmit={(e) => { e.preventDefault(); setSent(true); }}>
            <Field label="Email address" testId="invite-email" type="email" placeholder="teammate@company.com" />
            <Field label="Role" testId="invite-role" options={["Analyst", "Editor", "Admin"]} />
            <Button type="submit" testId="send-invite">Send invitation</Button>
          </form>
        )}
      </Card>
    </Page>
  );
}
