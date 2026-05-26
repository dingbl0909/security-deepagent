import type { SecurityTask } from "../types";

type TaskListProps = {
  tasks: SecurityTask[];
};

export function TaskList({ tasks }: TaskListProps) {
  return (
    <section className="card">
      <div className="section-header">
        <div>
          <p className="eyebrow">Checklist</p>
          <h3>排查任务</h3>
        </div>
        <span className="count">{tasks.length}</span>
      </div>

      {tasks.length === 0 ? (
        <p className="muted">暂无任务。复杂问题会自动拆解成待办。</p>
      ) : (
        <div className="stack">
          {tasks.map((task, index) => (
            <article className="task-item" key={task.id ?? `${task.title}-${index}`}>
              <strong>{task.title}</strong>
              <div>
                <span>{task.status}</span>
                {task.priority ? <span>{task.priority}</span> : null}
              </div>
              {task.details ? <p>{task.details}</p> : null}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
