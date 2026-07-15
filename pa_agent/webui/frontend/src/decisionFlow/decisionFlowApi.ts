import { post } from "../api/client";
import type { DecisionFlowResponse, DecisionTreeReplayRequest } from "../types/domain";

export function fetchDecisionFlow(
  body: DecisionTreeReplayRequest,
): Promise<DecisionFlowResponse> {
  return post<DecisionFlowResponse>("/api/decision-tree/flow", body);
}
