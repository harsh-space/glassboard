import type { Board, Task, Dependency, TaskExplanation, AISuggestion, DownstreamChange, ColumnType, ImpactPreviewResponse } from "./types";

const rawApiUrl = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
const API_BASE = rawApiUrl.endsWith("/api") ? rawApiUrl : `${rawApiUrl}/api`;

export class ApiRequestError extends Error {
  code: string;
  details?: Record<string, any>;

  constructor(code: string, message: string, details?: Record<string, any>) {
    super(message);
    this.name = "ApiRequestError";
    this.code = code;
    this.details = details;
  }
}

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem("auth_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
      ...(options?.headers || {}),
    },
  });

  if (response.status === 204) {
    return {} as T;
  }

  const data = await response.json();

  if (!response.ok) {
    // FastAPI raises HTTPException with detail={code, message, details}
    // Fall back to a generic format otherwise
    const detail = data.detail || data.error;
    const err = typeof detail === "object" && detail?.code
      ? detail
      : {
          code: `HTTP_${response.status}`,
          message: typeof detail === "string" ? detail : "An unexpected error occurred.",
          details: {},
        };
    throw new ApiRequestError(err.code, err.message, err.details);
  }

  return data as T;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface AuthUser {
  access_token: string;
  token_type: string;
  user_id: number;
  username: string;
  email: string;
}

export interface BoardSummary {
  id: number;
  name: string;
  start_date: string;
  task_count: number;
}

export const authApi = {
  register: (email: string, username: string, password: string): Promise<AuthUser> =>
    request<AuthUser>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, username, password }),
    }),

  login: (email: string, password: string): Promise<AuthUser> =>
    request<AuthUser>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: (): Promise<{ user_id: number; username: string; email: string }> =>
    request("/auth/me"),

  listBoards: (): Promise<BoardSummary[]> =>
    request<BoardSummary[]>("/auth/boards"),

  createBoard: (name: string, start_date: string): Promise<BoardSummary> =>
    request<BoardSummary>("/auth/boards", {
      method: "POST",
      body: JSON.stringify({ name, start_date }),
    }),
};

// ── Board / Task / Dependency API ─────────────────────────────────────────────

export const api = {
  getBoard: (boardId: number = 1): Promise<Board> => {
    return request<Board>(`/boards/${boardId}`);
  },

  createTask: (payload: {
    board_id: number;
    title: string;
    description?: string;
    duration_days: number;
    column?: string;
    position?: number;
  }): Promise<Task> => {
    return request<Task>("/tasks", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  updateTask: (
    taskId: number,
    payload: {
      title?: string;
      description?: string;
      duration_days?: number;
      pinned_start?: string | null;
      version: number;
    }
  ): Promise<{ task: Task; downstream_changes: DownstreamChange[] }> => {
    return request<{ task: Task; downstream_changes: DownstreamChange[] }>(`/tasks/${taskId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  moveTask: (
    taskId: number,
    payload: {
      column?: ColumnType;
      position?: number;
      version: number;
    }
  ): Promise<{ task: Task; downstream_changes: DownstreamChange[] }> => {
    return request<{ task: Task; downstream_changes: DownstreamChange[] }>(`/tasks/${taskId}/move`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  deleteTask: (taskId: number): Promise<void> => {
    return request<void>(`/tasks/${taskId}`, {
      method: "DELETE",
    });
  },

  createDependency: (
    taskId: number,
    prerequisiteId: number
  ): Promise<{ dependency: Dependency; downstream_changes: DownstreamChange[] }> => {
    return request<{ dependency: Dependency; downstream_changes: DownstreamChange[] }>("/dependencies", {
      method: "POST",
      body: JSON.stringify({ task_id: taskId, prerequisite_id: prerequisiteId }),
    });
  },

  deleteDependency: (
    dependencyId: number
  ): Promise<{ deleted_dependency_id: number; downstream_changes: DownstreamChange[] }> => {
    return request<{ deleted_dependency_id: number; downstream_changes: DownstreamChange[] }>(
      `/dependencies/${dependencyId}`,
      { method: "DELETE" }
    );
  },

  getTaskExplanation: (taskId: number): Promise<TaskExplanation> => {
    return request<TaskExplanation>(`/tasks/${taskId}/explanation`);
  },

  getPendingSuggestions: (boardId: number = 1): Promise<AISuggestion[]> => {
    return request<AISuggestion[]>(`/dependencies/suggestions?board_id=${boardId}`);
  },

  getAISuggestions: (boardId: number = 1, taskId?: number): Promise<AISuggestion[]> => {
    return request<AISuggestion[]>("/dependencies/suggestions", {
      method: "POST",
      body: JSON.stringify({ board_id: boardId, task_id: taskId }),
    });
  },

  getImpactPreview: (
    taskId: number,
    payload: { duration_days?: number; pinned_start?: string | null }
  ): Promise<ImpactPreviewResponse> => {
    return request<ImpactPreviewResponse>(`/tasks/${taskId}/impact-preview`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  acceptSuggestion: (
    suggestionId: number
  ): Promise<{ dependency: Dependency; downstream_changes: DownstreamChange[] }> => {
    return request<{ dependency: Dependency; downstream_changes: DownstreamChange[] }>(
      `/dependencies/suggestions/${suggestionId}/accept`,
      { method: "POST" }
    );
  },

  rejectSuggestion: (suggestionId: number): Promise<void> => {
    return request<void>(`/dependencies/suggestions/${suggestionId}/reject`, {
      method: "POST",
    });
  },

  getCriticalPath: (boardId: number = 1): Promise<{ task_ids: number[]; total_duration: number }> => {
    return request<{ task_ids: number[]; total_duration: number }>(`/boards/${boardId}/critical-path`);
  },
};
