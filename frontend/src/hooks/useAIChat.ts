/**
 * AI Chat Hooks
 *
 * React Query hooks for AI chat functionality.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { aiChatService, type ExecuteActionRequest } from "@/services/aiChat"

// =============================================================================
// Query Keys
// =============================================================================

export const aiChatKeys = {
  all: ["ai-chat"] as const,
  sessions: () => [...aiChatKeys.all, "sessions"] as const,
  session: (id: string) => [...aiChatKeys.all, "session", id] as const,
}

// =============================================================================
// Query Hooks
// =============================================================================

/**
 * Hook to list chat sessions.
 */
export function useChatSessions(includeInactive = false, limit = 10) {
  return useQuery({
    queryKey: aiChatKeys.sessions(),
    queryFn: () => aiChatService.listSessions(includeInactive, limit),
    staleTime: 60 * 1000,
  })
}

/**
 * Hook to get a specific chat session.
 */
export function useChatSession(sessionId: string | null) {
  return useQuery({
    queryKey: aiChatKeys.session(sessionId || ""),
    queryFn: () => aiChatService.getSession(sessionId!),
    enabled: !!sessionId,
    staleTime: 30 * 1000,
    refetchInterval: 5000, // Refetch every 5 seconds to get updated messages
  })
}

// =============================================================================
// Mutation Hooks
// =============================================================================

/**
 * Hook to send a chat message.
 */
export function useSendChatMessage(sessionId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (message: string) => aiChatService.sendMessage(sessionId, message),
    onSuccess: () => {
      // Invalidate session to get updated messages
      queryClient.invalidateQueries({ queryKey: aiChatKeys.session(sessionId) })
    },
  })
}

/**
 * Hook to end a chat session.
 */
export function useEndChatSession() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (sessionId: string) => aiChatService.endSession(sessionId),
    onSuccess: (_, sessionId) => {
      queryClient.invalidateQueries({ queryKey: aiChatKeys.session(sessionId) })
      queryClient.invalidateQueries({ queryKey: aiChatKeys.sessions() })
    },
  })
}

/**
 * Hook to execute an action from an action card.
 */
export function useExecuteAction(sessionId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: ExecuteActionRequest) =>
      aiChatService.executeAction(sessionId, request),
    onSuccess: () => {
      // Invalidate relevant queries
      queryClient.invalidateQueries({ queryKey: aiChatKeys.session(sessionId) })
      queryClient.invalidateQueries({ queryKey: ["video-planning"] })
    },
  })
}
