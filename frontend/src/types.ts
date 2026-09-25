export type ColumnType = "backlog" | "in_progress" | "review" | "done";

export interface SlackInfo {
  prerequisite_id: number;
  days: number;
}

export interface Task {
  id: number;
  board_id: number;
  title: string;
  description: string;
  column: ColumnType;
  position: number;
  duration_days: number;
  pinned_start: string | null;
  planned_start: string;
  planned_end: string;
  actual_end: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  blocked: boolean;
  ready: boolean;
  driving_prerequisite_id: number | null;
  slack: SlackInfo[];
  blocking_prerequisite_ids: number[];
}

export interface Dependency {
  id: number;
  task_id: number;
  prerequisite_id: number;
  created_at: string;
}

export interface Board {
  id: number;
  name: string;
  start_date: string;
  tasks: Task[];
  dependencies: Dependency[];
}

export interface DownstreamChange {
  task_id: number;
  old_start: string;
  new_start: string;
}

export interface TaskExplanation {
  driving_prerequisite_id: number | null;
  reason_text: string;
  slack: SlackInfo[];
}

export interface AISuggestion {
  id: number;
  task_id: number;
  prerequisite_id: number;
  reason: string;
  evidence_phrase: string;
  proposer_confidence: number;
  challenge_verdict: "not_run" | "survived" | "contested" | "rejected";
  status: "pending" | "accepted" | "rejected";
  model_name: string;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, any>;
}

export interface ImpactPreviewItem {
  task_id: number;
  old_start: string;
  new_start: string;
}

export interface ImpactPreviewResponse {
  would_change: ImpactPreviewItem[];
}
