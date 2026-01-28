/**
 * Suggestions Hooks
 * 
 * React Query hooks for AI suggestions functionality.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { suggestionsService } from "@/services/suggestions"
import type { SuggestionType } from "@/types"

// =============================================================================
// Types
// =============================================================================

export interface SuggestionsListParams {
  type?: SuggestionType
  include_read?: boolean
  include_dismissed?: boolean
  limit?: number
}

// =============================================================================
// Query Keys
// =============================================================================

export const suggestionsKeys = {
  all: ["suggestions"] as const,
  list: (params?: SuggestionsListParams) =>
    [...suggestionsKeys.all, "list", params] as const,
  unreadCount: () => [...suggestionsKeys.all, "unread-count"] as const,
  postingTimes: (days?: number) => [...suggestionsKeys.all, "posting-times", days] as const,
  contentIdeas: (count?: number) => [...suggestionsKeys.all, "content-ideas", count] as const,
  trends: (category?: string) => [...suggestionsKeys.all, "trends", category] as const,
  improvements: () => [...suggestionsKeys.all, "improvements"] as const,
}

// =============================================================================
// List Hooks
// =============================================================================

/**
 * Hook to fetch suggestions list.
 */
export function useSuggestions(params?: SuggestionsListParams) {
  return useQuery({
    queryKey: suggestionsKeys.list(params),
    queryFn: () => suggestionsService.list(params),
    staleTime: 60 * 1000,
  })
}

/**
 * Hook to fetch unread count.
 */
export function useSuggestionsUnreadCount() {
  return useQuery({
    queryKey: suggestionsKeys.unreadCount(),
    queryFn: () => suggestionsService.getUnreadCount(),
    staleTime: 30 * 1000,
  })
}

// =============================================================================
// Action Hooks
// =============================================================================

/**
 * Hook to mark suggestion as read.
 */
export function useMarkSuggestionRead() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (id: string) => suggestionsService.markAsRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: suggestionsKeys.all })
    },
  })
}

/**
 * Hook to mark all suggestions as read.
 */
export function useMarkAllSuggestionsRead() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: () => suggestionsService.markAllAsRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: suggestionsKeys.all })
    },
  })
}

/**
 * Hook to dismiss a suggestion.
 */
export function useDismissSuggestion() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) => 
      suggestionsService.dismiss(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: suggestionsKeys.all })
    },
  })
}

/**
 * Hook to mark suggestion as acted upon.
 */
export function useMarkSuggestionActed() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (id: string) => suggestionsService.markActedOn(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: suggestionsKeys.all })
    },
  })
}

/**
 * Hook to generate new suggestions.
 */
export function useGenerateSuggestions() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: () => suggestionsService.generate(),
    onSuccess: () => {
      // Invalidate after a delay to allow processing
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: suggestionsKeys.all })
      }, 5000)
    },
  })
}

/**
 * Hook to generate a smart AI suggestion with chat session.
 * Returns a complete suggestion with chat_session_id for follow-up.
 */
export function useGenerateSmartSuggestion() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: () => suggestionsService.generateSmart(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: suggestionsKeys.all })
    },
  })
}

// =============================================================================
// Analysis Hooks
// =============================================================================

/**
 * Hook to analyze posting times.
 */
export function usePostingTimesAnalysis(days?: number) {
  return useQuery({
    queryKey: suggestionsKeys.postingTimes(days),
    queryFn: () => suggestionsService.analyzePostingTimes(days),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Hook to fetch content ideas.
 */
export function useContentIdeas(count?: number) {
  return useQuery({
    queryKey: suggestionsKeys.contentIdeas(count),
    queryFn: () => suggestionsService.getContentIdeas(count),
    staleTime: 5 * 60 * 1000,
  })
}

/**
 * Hook to fetch trending topics.
 */
export function useTrends(category?: string) {
  return useQuery({
    queryKey: suggestionsKeys.trends(category),
    queryFn: () => suggestionsService.getTrends(category),
    staleTime: 5 * 60 * 1000,
  })
}

/**
 * Hook to fetch improvement suggestions.
 */
export function useImprovements() {
  return useQuery({
    queryKey: suggestionsKeys.improvements(),
    queryFn: () => suggestionsService.getImprovements(),
    staleTime: 5 * 60 * 1000,
  })
}
