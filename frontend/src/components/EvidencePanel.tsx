import type { Evidence } from "../types";

type EvidencePanelProps = {
  evidence: Evidence[];
};

export function EvidencePanel({ evidence }: EvidencePanelProps) {
  return (
    <section className="card">
      <div className="section-header">
        <div>
          <p className="eyebrow">RAG Evidence</p>
          <h3>知识库证据</h3>
        </div>
        <span className="count">{evidence.length}</span>
      </div>

      {evidence.length === 0 ? (
        <p className="muted">暂无证据。发送问题后会显示命中的知识库来源。</p>
      ) : (
        <div className="stack">
          {evidence.map((item) => (
            <article className="evidence-item" key={`${item.source}-${item.title}`}>
              <div className="item-title">
                <strong>{item.title}</strong>
                <span>{item.score.toFixed(2)}</span>
              </div>
              <p>{item.snippet}</p>
              <small>{item.source}</small>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
