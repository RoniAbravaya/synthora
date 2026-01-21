/**
 * AI Suggestions API Service
 */

import { apiClient } from "@/lib/api"
import type { Suggestion, SuggestionType } from "@/types"

export interface SuggestionListResponse {
  suggestions: Suggestion[]
  total: number
  unread_count: number
}

export interface PostingTimeSuggestion {
  platform: string
  day_of_week: number
  hour: number
  confidence: number
  reasoning: string
}

export interface ContentSuggestion {
  topic: string
  hook: string
  key_points: string[]
  call_to_action: string
  estimated_engagement: number
}

export interface TrendAlert {
  trend: string
  platform: string
  relevance_score: number
  suggested_angle: string
  expires_at: string
}

export interface PerformancePrediction {
  video_id: string
  predicted_views: number
  predicted_engagement: number
  confidence: number
  factors: string[]
}

export interface ImprovementTip {
  area: string
  current_score: number
  suggestion: string
  expected_improvement: number
  priority: "high" | "medium" | "low"
}

export const suggestionsService = {
  /**
   * Get all suggestions.
   */
  list: (params?: { type?: SuggestionType; unread_only?: boolean }) =>
    apiClient.get<SuggestionListResponse>("/suggestions", { params }),

  /**
   * Get unread count.
   */
  getUnreadCount: () =>
    apiClient.get<{ count: number }>("/suggestions/unread-count"),

  /**
   * Mark suggestion as read.
   */
  markAsRead: (id: string) =>
    apiClient.patch<{ message: string }>(`/suggestions/${id}/read`),

  /**
   * Dismiss a suggestion.
   */
  dismiss: (id: string) =>
    apiClient.patch<{ message: string }>(`/suggestions/${id}/dismiss`),

  /**
   * Mark suggestion as acted upon.
   */
  markActedOn: (id: string) =>
    apiClient.patch<{ message: string }>(`/suggestions/${id}/acted`),

  /**
   * Get optimal posting times.
   */
  getPostingTimes: () =>
    apiClient.get<{ suggestions: PostingTimeSuggestion[] }>("/suggestions/posting-times"),

  /**
   * Get content ideas.
   */
  getContentIdeas: (count?: number) =>
    apiClient.get<{ suggestions: ContentSuggestion[] }>("/suggestions/content", { params: { count } }),

  /**
   * Get trend alerts.
   */
  getTrends: () =>
    apiClient.get<{ alerts: TrendAlert[] }>("/suggestions/trends"),

  /**
   * Get performance predictions.
   */
  getPredictions: () =>
    apiClient.get<{ predictions: PerformancePrediction[] }>("/suggestions/predictions"),

  /**
   * Get improvement tips.
   */
  getImprovements: () =>
    apiClient.get<{ tips: ImprovementTip[] }>("/suggestions/improvements"),
}

