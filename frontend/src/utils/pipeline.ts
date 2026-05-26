import type { ChatResponse, HealthResponse } from "../types";

export type PipelineMode = "local" | "deep-agent" | "deep-agent-ready" | "unknown";

export type PipelineDisplay = {
  label: string;
  mode: PipelineMode;
};

export function resolvePipelineFromHealth(health: HealthResponse | undefined): PipelineDisplay {
  if (!health) {
    return { label: "链路检测中...", mode: "unknown" };
  }
  if (health.llm_enabled) {
    return { label: "DeepAgent 就绪", mode: "deep-agent-ready" };
  }
  return { label: "本地生产链路", mode: "local" };
}

export function resolvePipelineFromResponse(response: ChatResponse): PipelineDisplay {
  const usesDeepAgent = response.react_trace.some((step) => step.includes("DeepAgent"));
  if (usesDeepAgent) {
    return { label: "DeepAgent + 大模型编排链路", mode: "deep-agent" };
  }
  if (response.answer.includes("已按本地生产链路")) {
    return { label: "本地生产链路", mode: "local" };
  }
  return { label: "本地生产链路", mode: "local" };
}

export function resolveCurrentPipeline(
  health: HealthResponse | undefined,
  latestResponse: ChatResponse | undefined,
): PipelineDisplay {
  if (latestResponse) {
    return resolvePipelineFromResponse(latestResponse);
  }
  return resolvePipelineFromHealth(health);
}
