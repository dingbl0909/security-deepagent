type TraceTimelineProps = {
  trace: string[];
};

export function TraceTimeline({ trace }: TraceTimelineProps) {
  return (
    <section className="card">
      <div className="section-header">
        <div>
          <p className="eyebrow">Audit Trail</p>
          <h3>执行轨迹</h3>
        </div>
        <span className="count">{trace.length}</span>
      </div>

      {trace.length === 0 ? (
        <p className="muted">暂无 ReAct 轨迹。</p>
      ) : (
        <ol className="timeline">
          {trace.map((step, index) => (
            <li key={`${index}-${step}`}>
              <span>{index + 1}</span>
              <p>{step}</p>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
