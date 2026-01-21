/**
 * Notifications Hook
 * 
 * Manages notification state and actions.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "@/lib/api"
import type { Notification, PaginatedResponse } from "@/types"

// =============================================================================
// Query Keys
// =============================================================================

export const notificationKeys = {
  all: ["notifications"] as const,
  list: () => [...notificationKeys.all, "list"] as const,
  unreadCount: () => [...notificationKeys.all, "unread-count"] as const,
}

// =============================================================================
// Hooks
// =============================================================================

/**
 * Hook to fetch notifications.
 */
export function useNotifications(limit = 20) {
  return useQuery({
    queryKey: notificationKeys.list(),
    queryFn: () =>
      apiClient.get<PaginatedResponse<Notification>>(`/notifications?limit=${limit}`),
  })
}

/**
 * Hook to fetch unread notification count.
 */
export function useUnreadCount() {
  return useQuery({
    queryKey: notificationKeys.unreadCount(),
    queryFn: () =>
      apiClient.get<{ count: number }>("/notifications/unread-count"),
    refetchInterval: 30000, // Refetch every 30 seconds
  })
}

/**
 * Hook to mark notification as read.
 */
export function useMarkAsRead() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (notificationId: string) =>
      apiClient.patch(`/notifications/${notificationId}/read`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationKeys.all })
    },
  })
}

/**
 * Hook to mark all notifications as read.
 */
export function useMarkAllAsRead() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => apiClient.patch("/notifications/read-all"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationKeys.all })
    },
  })
}

/**
 * Hook to dismiss a notification.
 */
export function useDismissNotification() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (notificationId: string) =>
      apiClient.patch(`/notifications/${notificationId}/dismiss`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationKeys.all })
    },
  })
}

