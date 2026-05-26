import type { FormEvent } from "react";
import { ImageUpload } from "./ImageUpload";
import type { ChatResponse } from "../types";
import type { SelectedImage } from "../utils/image";
import type { PipelineDisplay } from "../utils/pipeline";
import { resolvePipelineFromResponse } from "../utils/pipeline";

type ChatPanelProps = {
  message: string;
  setMessage: (message: string) => void;
  selectedImage: SelectedImage | null;
  imageError?: string;
  visionEnabled?: boolean;
  onImageSelect: (file: File) => void;
  onImageClear: () => void;
  responses: ChatResponse[];
  loading: boolean;
  pipeline: PipelineDisplay;
  onSubmit: () => void;
};

const examples = [
  "仓库北门摄像头离线，帮我根据知识库排查原因，并给出下一步建议。",
  "布控告警频繁误报，可能是什么原因？",
  "请识别这张抓拍图里的异常物品，并给出安防研判。",
  "需要重启服务并修改配置，帮我评估风险。",
];

export function ChatPanel({
  message,
  setMessage,
  selectedImage,
  imageError,
  visionEnabled = false,
  onImageSelect,
  onImageClear,
  responses,
  loading,
  pipeline,
  onSubmit,
}: ChatPanelProps) {
  const canSubmit = Boolean(message.trim() || selectedImage);

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
        <ImageUpload
          selectedImage={selectedImage}
          disabled={loading}
          visionEnabled={visionEnabled}
          onSelect={onImageSelect}
          onClear={onImageClear}
          error={imageError}
        />

        <textarea
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="描述设备、告警、部署、现场问题，或上传图片后进行物品研判..."
          rows={5}
        />
        <button type="submit" disabled={loading || !canSubmit}>
          {loading ? "分析中..." : selectedImage ? "发送图片研判" : "发送分析"}
        </button>
      </form>

      <div className="conversation">
        {responses.length === 0 ? (
          <div className="empty-state">输入问题或上传图片后，助手会返回建议、证据、轨迹和风险判断。</div>
        ) : (
          responses.map((response, index) => {
            const responsePipeline = resolvePipelineFromResponse(response);
            return (
              <article className="assistant-message" key={`${response.thread_id}-${index}`}>
                <div className="message-meta">
                  <span className={`status-dot status-dot--${responsePipeline.mode}`}>{responsePipeline.label}</span>
                  {response.intent ? <span>{response.intent}</span> : null}
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
