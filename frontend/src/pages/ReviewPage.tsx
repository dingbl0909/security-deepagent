import { useEffect, useState } from "react";
import { continueReview, listReviews } from "../api/client";
import type { ReviewRequest } from "../types";

export function ReviewPage() {
  const [reviews, setReviews] = useState<ReviewRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  async function refresh() {
    setLoading(true);
    setError(undefined);
    try {
      setReviews(await listReviews("pending"));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "加载审核列表失败");
    } finally {
      setLoading(false);
    }
  }

  async function decide(reviewId: number, approve: boolean) {
    setError(undefined);
    try {
      await continueReview(reviewId, approve);
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "提交审核失败");
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <main className="page-grid">
      <section className="card full-span">
        <div className="section-header">
          <div>
            <p className="eyebrow">Manual Review</p>
            <h2>人工确认</h2>
          </div>
          <button type="button" onClick={() => void refresh()}>
            刷新
          </button>
        </div>

        {error ? <div className="error-banner">{error}</div> : null}
        {loading ? <p className="muted">加载中...</p> : null}
        {!loading && reviews.length === 0 ? <p className="muted">暂无待确认请求。</p> : null}

        <div className="review-list">
          {reviews.map((review) => (
            <article className="review-row" key={review.id}>
              <div>
                <strong>#{review.id} · 风险等级 {review.risk_level}</strong>
                <div className="review-field">
                  <span className="review-label">待确认动作</span>
                  <p>{review.proposed_action}</p>
                </div>
                <div className="review-field">
                  <span className="review-label">触发原因</span>
                  <p>{review.reason}</p>
                </div>
              </div>
              <div className="review-actions">
                <button type="button" onClick={() => void decide(review.id, true)}>
                  批准
                </button>
                <button type="button" onClick={() => void decide(review.id, false)}>
                  拒绝
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
