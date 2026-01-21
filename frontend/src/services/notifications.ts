/**
 * Notifications API Service
 */

import { apiClient } from "@/lib/api"
import type { Notification, NotificationType } from "@/types"

export interface NotificationListResponse {
  notifications: Notification[]
  total: number
  unread_count: number
}

export const notificationsService = {
  /**
   * Get notifications.
   */
  list: (params?: { type?: NotificationType; unread_only?: boolean; limit?: number }) =>
    apiClient.get<NotificationListResponse>("/notifications", { params }),

  /**
   * Get unread count.
   */
  getUnreadCount: () =>
    apiClient.get<{ count: number }>("/notifications/unread-count"),

  /**
   * Mark notification as read.
   */
  markAsRead: (id: string) =>
    apiClient.patch<{ message: string }>(`/notifications/${id}/read`),

  /**
   * Mark all as read.
   */
  markAllAsRead: () =>
    apiClient.patch<{ message: string; count: number }>("/notifications/read-all"),

  /**
   * Dismiss notification.
   */
  dismiss: (id: string) =>
    apiClient.patch<{ message: string }>(`/notifications/${id}/dismiss`),

  /**
   * Delete notification.
   */
  delete: (id: string) =>
    apiClient.delete<{ message: string }>(`/notifications/${id}`),
}

