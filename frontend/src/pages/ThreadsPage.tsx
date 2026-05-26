import { useEffect, useState } from "react";
import { getThread, listThreads } from "../api/client";
import type { ThreadDetail, ThreadSummary } from "../types";

export function ThreadsPage() {
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [selected, setSelected] = useState<ThreadDetail>();
  const [error, setError] = useState<string>();

  async function loadThreads() {
    setError(undefined);
    try {
      const data = await listThreads();
      setThreads(data);
      if (data[0]) {
        setSelected(await getThread(data[0].thread_id));
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "加载会话失败");
    }
  }

  async function openThread(threadId: string) {
    setError(undefined);
    try {
      setSelected(await getThread(threadId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "加载会话详情失败");
    }
  }

  useEffect(() => {
    void loadThreads();
  }, []);

  return (
    <main className="page-grid two-column">
      <section className="card">
        <div className="section-header">
          <div>
            <p className="eyebrow">Threads</p>
            <h2>历史会话</h2>
          </div>
          <button type="button" onClick={() => void loadThreads()}>
            刷新
          </button>
        </div>
        {error ? <div className="error-banner">{error}</div> : null}
        <div className="thread-list">
          {threads.map((thread) => (
            <button key={thread.thread_id} type="button" onClick={() => void openThread(thread.thread_id)}>
              <strong>{thread.title || thread.thread_id}</strong>
              <span>{thread.message_count} 条消息 · 待审 {thread.pending_review_count}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="card">
        <div className="section-header">
          <div>
            <p className="eyebrow">Traceable Record</p>
            <h2>会话详情</h2>
          </div>
        </div>
        {!selected ? <p className="muted">请选择一个会话。</p> : null}
        {selected ? (
          <div className="thread-detail">
            {selected.messages.map((message, index) => (
              <article className={`history-message ${message.role}`} key={`${message.created_at}-${index}`}>
                <strong>{message.role}</strong>
                <p>{message.content}</p>
                <small>{message.created_at}</small>
              </article>
            ))}
          </div>
        ) : null}
      </section>
    </main>
  );
}
