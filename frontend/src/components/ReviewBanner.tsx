type ReviewBannerProps = {
  reviewId: number | null;
  riskLevel: string;
  needsReview: boolean;
  reviewReason?: string | null;
  proposedAction?: string | null;
  riskKeywords?: string[];
  submitting: boolean;
  status?: string;
  onDecision: (approve: boolean) => void;
};

export function ReviewBanner({
  reviewId,
  riskLevel,
  needsReview,
  reviewReason,
  proposedAction,
  riskKeywords = [],
  submitting,
  status,
  onDecision,
}: ReviewBannerProps) {
  if (!needsReview || reviewId === null) {
    return (
      <section className="card review-safe">
        <p className="eyebrow">Risk Control</p>
        <h3>未触发人工确认</h3>
        <p className="muted">当前请求风险等级为 {riskLevel || "low"}。</p>
      </section>
    );
  }

  return (
    <section className="card review-banner">
      <p className="eyebrow">Risk Control</p>
      <h3>需要人工确认</h3>
      <p className="review-meta">
        风险等级：<strong>{riskLevel}</strong> · review_id={reviewId}
      </p>

      <div className="review-detail">
        <div className="review-field">
          <span className="review-label">待确认动作</span>
          <p>{proposedAction || "未提供明确动作描述。"}</p>
        </div>

        {reviewReason ? (
          <div className="review-field">
            <span className="review-label">触发原因</span>
            <p>{reviewReason}</p>
          </div>
        ) : null}

        {riskKeywords.length > 0 ? (
          <div className="review-field">
            <span className="review-label">命中关键词</span>
            <div className="keyword-list">
              {riskKeywords.map((keyword) => (
                <span className="keyword-chip" key={keyword}>
                  {keyword}
                </span>
              ))}
            </div>
          </div>
        ) : null}
      </div>

      {status ? <p className="decision-status">处理结果：{status}</p> : null}
      <div className="review-actions">
        <button type="button" disabled={submitting || Boolean(status)} onClick={() => onDecision(true)}>
          批准
        </button>
        <button type="button" disabled={submitting || Boolean(status)} onClick={() => onDecision(false)}>
          拒绝
        </button>
      </div>
    </section>
  );
}
