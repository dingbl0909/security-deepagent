import { useEffect, useMemo, useState } from "react";
import { continueReview, getHealth, sendChat } from "../api/client";
import { ChatPanel } from "../components/ChatPanel";
import { EvidencePanel } from "../components/EvidencePanel";
import { ReviewBanner } from "../components/ReviewBanner";
import { TaskList } from "../components/TaskList";
import { TraceTimeline } from "../components/TraceTimeline";
import type { ChatResponse, HealthResponse } from "../types";
import { readImageFile, type SelectedImage } from "../utils/image";
import { resolveCurrentPipeline } from "../utils/pipeline";

const DEFAULT_VISION_MESSAGE = "请识别这张图片中的安防相关物品，并给出研判结论。";

export function WorkspacePage() {
  const [message, setMessage] = useState("");
  const [selectedImage, setSelectedImage] = useState<SelectedImage | null>(null);
  const [imageError, setImageError] = useState<string>();
  const [responses, setResponses] = useState<ChatResponse[]>([]);
  const [health, setHealth] = useState<HealthResponse>();
  const [loading, setLoading] = useState(false);
  const [reviewStatus, setReviewStatus] = useState<string>();
  const [reviewSubmitting, setReviewSubmitting] = useState(false);
  const [error, setError] = useState<string>();
  const threadId = useMemo(() => `web-${new Date().toISOString().slice(0, 10)}`, []);
  const latest = responses.length > 0 ? responses[responses.length - 1] : undefined;
  const pipeline = resolveCurrentPipeline(health, latest, Boolean(selectedImage));

  useEffect(() => {
    void getHealth()
      .then(setHealth)
      .catch((caught) => {
        setError(caught instanceof Error ? caught.message : "无法读取后端健康状态");
      });
  }, []);

  async function handleImageSelect(file: File) {
    setImageError(undefined);
    try {
      setSelectedImage(await readImageFile(file));
    } catch (caught) {
      setImageError(caught instanceof Error ? caught.message : "图片读取失败");
    }
  }

  async function handleSubmit() {
    const finalMessage = message.trim() || (selectedImage ? DEFAULT_VISION_MESSAGE : "");
    if (!finalMessage) {
      return;
    }
    setLoading(true);
    setError(undefined);
    setReviewStatus(undefined);
    try {
      const response = await sendChat({
        message: finalMessage,
        thread_id: threadId,
        user_id: "ops_001",
        image_base64: selectedImage?.base64 ?? null,
      });
      setResponses((current) => [...current, response]);
      setMessage("");
      setSelectedImage(null);
      setImageError(undefined);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "请求失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleReview(approve: boolean) {
    if (!latest?.review_id) {
      return;
    }
    setReviewSubmitting(true);
    setError(undefined);
    try {
      const result = await continueReview(latest.review_id, approve);
      setReviewStatus(result.status);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "人工确认失败");
    } finally {
      setReviewSubmitting(false);
    }
  }

  return (
    <main className="workspace">
      <ChatPanel
        message={message}
        setMessage={setMessage}
        selectedImage={selectedImage}
        imageError={imageError}
        visionEnabled={health?.vision_enabled}
        onImageSelect={(file) => void handleImageSelect(file)}
        onImageClear={() => {
          setSelectedImage(null);
          setImageError(undefined);
        }}
        responses={responses}
        loading={loading}
        pipeline={pipeline}
        onSubmit={() => void handleSubmit()}
      />

      <aside className="insight-column">
        {error ? <div className="error-banner">{error}</div> : null}
        <ReviewBanner
          reviewId={latest?.review_id ?? null}
          riskLevel={latest?.risk_level ?? "low"}
          needsReview={latest?.needs_review ?? false}
          reviewReason={latest?.review_reason}
          proposedAction={latest?.proposed_action}
          riskKeywords={latest?.risk_keywords ?? []}
          submitting={reviewSubmitting}
          status={reviewStatus}
          onDecision={handleReview}
        />
        <EvidencePanel evidence={latest?.evidence ?? []} />
        <TraceTimeline trace={latest?.react_trace ?? []} />
        <TaskList tasks={latest?.tasks ?? []} />
      </aside>
    </main>
  );
}
