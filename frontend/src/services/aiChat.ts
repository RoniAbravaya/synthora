/**
 * AI Chat API Service
 *
 * API client for AI chat functionality including session management
 * and message processing.
 */

import { apiClient } from "@/lib/api"
import type { ChatSession, ChatMessageResponse } from "@/types"

// =============================================================================
// Types
// =============================================================================

export interface ChatSessionListItem {
  id: string
  is_active: boolean
  message_count: number
  last_message_at: string | null
  created_at: string
}

export interface ChatSessionListResponse {
  sessions: ChatSessionListItem[]
  total: number
}

export interface ExecuteActionRequest {
  action_type: string
  action_data: Record<string, unknown>
  scheduled_time?: string
  target_platforms?: string[]
}

export interface ExecuteActionResponse {
  success: boolean
  message: string
  created_video_ids?: string[]
  redirect_url?: string
}

// =============================================================================
// Service
// =============================================================================

export const aiChatService = {
  /**
   * List user's chat sessions.
   */
  listSessions: (includeInactive = false, limit = 10) =>
    apiClient.get<ChatSessionListResponse>("/ai-chat/sessions", {
      params: { include_inactive: includeInactive, limit },
    }),

  /**
   * Get a specific chat session.
   */
  getSession: (sessionId: string) =>
    apiClient.get<ChatSession>(`/ai-chat/sessions/${sessionId}`),

  /**
   * Send a message in a chat session.
   */
  sendMessage: (sessionId: string, message: string) =>
    apiClient.post<ChatMessageResponse>(`/ai-chat/sessions/${sessionId}/messages`, {
      message,
    }),

  /**
   * End a chat session.
   */
  endSession: (sessionId: string) =>
    apiClient.post<{ message: string }>(`/ai-chat/sessions/${sessionId}/end`),

  /**
   * Execute an action from an action card.
   */
  executeAction: (sessionId: string, request: ExecuteActionRequest) =>
    apiClient.post<ExecuteActionResponse>(
      `/ai-chat/sessions/${sessionId}/execute-action`,
      request
    ),
}
