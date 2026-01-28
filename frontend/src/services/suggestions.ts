/**
 * AI Suggestions API Service
 */

import { apiClient } from "@/lib/api"
import type { SuggestionType, SmartSuggestionResponse } from "@/types"

// =============================================================================
// Types
// =============================================================================

export interface SuggestionItem {
  id: string
  suggestion_type: string
  title: string
  description: string
  priority: string
  is_read: boolean
  action_type: string | null
  expires_at: string | null
  created_at: string
}

export interface SuggestionListResponse {
  suggestions: SuggestionItem[]
  total: number
  unread_count: number
}

export interface PostingTimeAnalysis {
  best_day: string
  best_day_index: number
  best_hour: number
  potential_improvement: number
  current_avg_engagement: number
  best_avg_engagement: number
}

export interface PostingTimeResponse {
  success: boolean
  posts_analyzed: number
  period_days: number
  overall: PostingTimeAnalysis | null
  by_platform: Record<string, PostingTimeAnalysis>
  error: string | null
}

export interface ContentIdea {
  topic: string
  hook: string
  description: string
  suggested_hashtags: string[]
  estimated_engagement: string
}

export interface ContentIdeasResponse {
  ideas: ContentIdea[]
}

export interface TrendItem {
  topic: string
  description: string
  platforms: string[]
  virality_score: number
  suggested_angle: string
  relevance_score: number | null
}

export interface TrendsResponse {
  trends: TrendItem[]
}

export interface ImprovementItem {
  category: string
  issue: string
  suggestion: string
  impact: string
}

export interface UnderperformingPost {
  post_id: string
  title: string | null
  current_engagement: number
  improvements: ImprovementItem[]
}

export interface ImprovementsResponse {
  underperforming_posts: UnderperformingPost[]
}

// =============================================================================
// Service
// =============================================================================

export const suggestionsService = {
  /**
   * Get all suggestions.
   */
  list: (params?: { 
    type?: SuggestionType
    include_read?: boolean
    include_dismissed?: boolean
    limit?: number
  }) =>
    apiClient.get<SuggestionListResponse>("/suggestions", { 
      params: {
        suggestion_type: params?.type,
        include_read: params?.include_read,
        include_dismissed: params?.include_dismissed,
        limit: params?.limit,
      }
    }),

  /**
   * Get unread count.
   */
  getUnreadCount: () =>
    apiClient.get<{ count: number }>("/suggestions/unread-count"),

  /**
   * Mark suggestion as read.
   */
  markAsRead: (id: string) =>
    apiClient.post<unknown>(`/suggestions/${id}/read`),

  /**
   * Mark all suggestions as read.
   */
  markAllAsRead: () =>
    apiClient.post<{ message: string }>("/suggestions/read-all"),

  /**
   * Dismiss a suggestion.
   */
  dismiss: (id: string, reason?: string) =>
    apiClient.post<unknown>(`/suggestions/${id}/dismiss`, { reason }),

  /**
   * Mark suggestion as acted upon.
   */
  markActedOn: (id: string) =>
    apiClient.post<unknown>(`/suggestions/${id}/acted`),

  /**
   * Analyze posting times.
   */
  analyzePostingTimes: (days?: number) =>
    apiClient.get<PostingTimeResponse>("/suggestions/analysis/posting-times", { params: { days } }),

  /**
   * Get content ideas.
   */
  getContentIdeas: (count?: number) =>
    apiClient.get<ContentIdeasResponse>("/suggestions/analysis/content-ideas", { params: { count } }),

  /**
   * Get trending topics.
   */
  getTrends: (category?: string) =>
    apiClient.get<TrendsResponse>("/suggestions/analysis/trends", { params: { category } }),

  /**
   * Get improvement suggestions.
   */
  getImprovements: () =>
    apiClient.get<ImprovementsResponse>("/suggestions/analysis/improvements"),

  /**
   * Generate new suggestions.
   */
  generate: () =>
    apiClient.post<{ message: string; job_id: string; estimated_time: string }>("/suggestions/generate"),

  /**
   * Generate a smart AI suggestion based on user data.
   * Checks data sufficiency and generates personalized or trend-based suggestion.
   * Creates a chat session for follow-up conversation.
   */
  generateSmart: () =>
    apiClient.post<SmartSuggestionResponse>("/suggestions/generate-smart"),
}

