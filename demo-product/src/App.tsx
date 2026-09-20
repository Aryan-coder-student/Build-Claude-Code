import { NavLink, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Projects from "./pages/Projects";
import AnalyticsOverview from "./pages/AnalyticsOverview";
import Reports from "./pages/Reports";
import Members from "./pages/Members";
import Invite from "./pages/Invite";
import Billing from "./pages/Billing";

const NAV = [
  { to: "/", label: "Dashboard", testId: "dashboard-nav", end: true },
  { to: "/projects", label: "Projects", testId: "projects-nav" },
  { to: "/analytics", label: "Analytics", testId: "analytics-nav", end: true },
  { to: "/analytics/reports", label: "Reports", testId: "reports-nav", child: true },
  { to: "/team", label: "Team", testId: "team-nav", end: true },
  { to: "/team/invite", label: "Invite Member", testId: "invite-nav", child: true },
  { to: "/billing", label: "Billing", testId: "billing-nav" },
];

export default function App() {
  return (
    <div className="flex min-h-screen">
      <aside className="w-60 shrink-0 border-r border-slate-200 bg-white" data-testid="sidebar">
        <div className="flex items-center gap-2 px-5 py-5">
          <div className="h-8 w-8 rounded-lg bg-indigo-600" />
          <span className="text-lg font-semibold tracking-tight">Lumen</span>
        </div>
        <nav className="px-3" aria-label="Main navigation">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              data-testid={item.testId}
              className={({ isActive }) =>
                `my-0.5 block rounded-lg px-3 py-2 text-sm ${item.child ? "ml-4" : ""} ${isActive ? "bg-indigo-50 font-medium text-indigo-700" : "text-slate-600 hover:bg-slate-100"}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 px-10 py-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/analytics" element={<AnalyticsOverview />} />
          <Route path="/analytics/reports" element={<Reports />} />
          <Route path="/team" element={<Members />} />
          <Route path="/team/invite" element={<Invite />} />
          <Route path="/billing" element={<Billing />} />
        </Routes>
      </main>
    </div>
  );
}
