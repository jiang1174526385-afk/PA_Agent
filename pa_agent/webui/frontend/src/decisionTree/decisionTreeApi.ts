import { get, post } from "../api/client";
import type {
  DecisionTreeReplayRequest,
  DecisionTreeReplayResponse,
  DecisionTreeStaticResponse,
} from "../types/domain";

export function fetchStaticDecisionTree(): Promise<DecisionTreeStaticResponse> {
  return get<DecisionTreeStaticResponse>("/api/decision-tree/static");
}

export function replayDecisionTrace(
  body: DecisionTreeReplayRequest,
): Promise<DecisionTreeReplayResponse> {
  return post<DecisionTreeReplayResponse>("/api/decision-tree/replay", body);
}
