import { useState } from "react";
import { OverviewPage } from "./pages/OverviewPage";
import { ReviewPage } from "./pages/ReviewPage";
import { ThreadsPage } from "./pages/ThreadsPage";
import { WorkspacePage } from "./pages/WorkspacePage";

type Page = "workspace" | "overview" | "threads" | "reviews";

const navItems: { id: Page; label: string }[] = [
  { id: "workspace", label: "智能工作台" },
  { id: "overview", label: "业务概览" },
  { id: "threads", label: "历史会话" },
  { id: "reviews", label: "人工确认" },
];

export function App() {
  const [page, setPage] = useState<Page>("workspace");

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Security DeepAgent</p>
          <h1>安防智能助手</h1>
        </div>
        <nav>
          {navItems.map((item) => (
            <button
              key={item.id}
              type="button"
              className={page === item.id ? "active" : ""}
              onClick={() => setPage(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </header>

      {page === "workspace" ? <WorkspacePage /> : null}
      {page === "overview" ? <OverviewPage /> : null}
      {page === "threads" ? <ThreadsPage /> : null}
      {page === "reviews" ? <ReviewPage /> : null}
    </div>
  );
}
