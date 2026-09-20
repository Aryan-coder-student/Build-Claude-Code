import { useNavigate } from "react-router-dom";
import { Button, Page, Table } from "../ui";

const MEMBERS = [
  ["Maya Chen", "maya@acme.io", "Admin", "Active"],
  ["Jordan Lee", "jordan@acme.io", "Editor", "Active"],
  ["Sam Patel", "sam@acme.io", "Analyst", "Invited"],
];

export default function Members() {
  const navigate = useNavigate();
  return (
    <Page
      title="Team"
      subtitle="Manage who has access to your workspace and what they can do."
      actions={<Button testId="invite-member" onClick={() => navigate("/team/invite")}>Invite Member</Button>}
    >
      <Table head={["Name", "Email", "Role", "Status"]} rows={MEMBERS} />
    </Page>
  );
}
