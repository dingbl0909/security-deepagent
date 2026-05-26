import type { FormEvent } from "react";
import type { ChatResponse } from "../types";
import type { PipelineDisplay } from "../utils/pipeline";
import { resolvePipelineFromResponse } from "../utils/pipeline";

type ChatPanelProps = {
  message: string;
  setMessage: (message: string) => void;
  responses: ChatResponse[];
  loading: boolean;
  pipeline: PipelineDisplay;
  onSubmit: () => void;
};

const examples = [
  "仓库北门摄像头离线，帮我根据知识库排查原因，并给出下一步建议。",
  "布控告警频繁误报，可能是什么原因？",
  "私有化部署后接口异常，如何定位？",
  "需要重启服务并修改配置，帮我评估风险。",
];

export function ChatPanel({ message, setMessage, responses, loading, pipeline, onSubmit }: ChatPanelProps) {
  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <section className="card chat-card">
      <div className="section-header">
        <div>
          <p className="eyebrow">Security Copilot</p>
          <h2>安防助手</h2>
        </div>
        <span className={`status-dot status-dot--${pipeline.mode}`}>{pipeline.label}</span>
      </div>

      <div className="examples">
        {examples.map((example) => (
          <button key={example} type="button" onClick={() => setMessage(example)}>
            {example}
          </button>
        ))}
      </div>

      <form className="chat-form" onSubmit={handleSubmit}>
        <textarea
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="描述设备、告警、部署或现场问题..."
          rows={5}
        />
        <button type="submit" disabled={loading || !message.trim()}>
          {loading ? "分析中..." : "发送分析"}
        </button>
      </form>

      <div className="conversation">
        {responses.length === 0 ? (
          <div className="empty-state">输入一个安防问题后，助手会返回建议、证据、轨迹和风险判断。</div>
        ) : (
          responses.map((response, index) => {
            const responsePipeline = resolvePipelineFromResponse(response);
            return (
            <article className="assistant-message" key={`${response.thread_id}-${index}`}>
              <div className="message-meta">
                <span className={`status-dot status-dot--${responsePipeline.mode}`}>{responsePipeline.label}</span>
                <span>风险：{response.risk_level}</span>
                <span>证据 {response.evidence.length} 条</span>
              </div>
              <p>{response.answer}</p>
            </article>
            );
          })
        )}
      </div>
    </section>
  );
}
