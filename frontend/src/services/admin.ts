/**
 * Admin API Service
 */

import { apiClient } from "@/lib/api"
import type { User, UserRole } from "@/types"

export interface AdminUserListResponse {
  users: Array<{
    id: string
    email: string
    display_name: string | null
    role: UserRole
    is_active: boolean
    created_at: string
    last_login: string | null
  }>
  total: number
  limit: number
  offset: number
  has_more: boolean
}

export interface AdminUserDetailResponse {
  id: string
  email: string
  display_name: string | null
  photo_url: string | null
  role: UserRole
  is_active: boolean
  created_at: string
  updated_at: string | null
  last_login: string | null
  subscription_status: string | null
  subscription_plan: string | null
  stats: {
    videos: number
    posts: number
    integrations: number
    social_accounts: number
  }
}

export interface PlatformStats {
  users: {
    total: number
    active: number
    new_30d: number
    by_role: Record<string, number>
  }
  videos: {
    total: number
    by_status: Record<string, number>
  }
  posts: {
    total: number
    by_status: Record<string, number>
  }
  subscriptions: {
    total: number
    active: number
    by_plan: Record<string, number>
    mrr: number
    arr: number
  }
}

export interface ActivityStats {
  period_days: number
  daily_signups: Array<{ date: string; count: number }>
  daily_videos: Array<{ date: string; count: number }>
  daily_posts: Array<{ date: string; count: number }>
}

export interface TopUser {
  user_id: string
  email: string
  display_name: string | null
  role: string
  count: number
}

export const adminService = {
  /**
   * List users with filters.
   */
  listUsers: (params?: {
    search?: string
    role?: UserRole
    is_active?: boolean
    sort_by?: string
    sort_order?: "asc" | "desc"
    limit?: number
    offset?: number
  }) => apiClient.get<AdminUserListResponse>("/admin/users", { params }),

  /**
   * Get user details.
   */
  getUserDetails: (userId: string) =>
    apiClient.get<AdminUserDetailResponse>(`/admin/users/${userId}`),

  /**
   * Update user role.
   */
  updateUserRole: (userId: string, role: UserRole) =>
    apiClient.patch<{ message: string; user_id: string; new_role: string }>(
      `/admin/users/${userId}/role`,
      { role }
    ),

  /**
   * Update user status.
   */
  updateUserStatus: (userId: string, isActive: boolean) =>
    apiClient.patch<{ message: string; user_id: string; is_active: boolean }>(
      `/admin/users/${userId}/status`,
      { is_active: isActive }
    ),

  /**
   * Delete user.
   */
  deleteUser: (userId: string, hardDelete?: boolean) =>
    apiClient.delete<{ message: string; user_id: string }>(
      `/admin/users/${userId}`,
      { params: { hard_delete: hardDelete } }
    ),

  /**
   * Get platform statistics.
   */
  getStats: () =>
    apiClient.get<PlatformStats>("/admin/stats"),

  /**
   * Get activity statistics.
   */
  getActivityStats: (days?: number) =>
    apiClient.get<ActivityStats>("/admin/stats/activity", { params: { days } }),

  /**
   * Get top users.
   */
  getTopUsers: (metric?: "videos" | "posts", limit?: number) =>
    apiClient.get<{ metric: string; users: TopUser[] }>("/admin/stats/top-users", {
      params: { metric, limit },
    }),

  /**
   * Get all settings.
   */
  getSettings: () =>
    apiClient.get<{ settings: Record<string, unknown> }>("/admin/settings"),

  /**
   * Get a specific setting.
   */
  getSetting: (key: string) =>
    apiClient.get<{ key: string; value: unknown }>(`/admin/settings/${key}`),

  /**
   * Set a setting.
   */
  setSetting: (key: string, value: unknown, description?: string) =>
    apiClient.post<{ message: string; key: string; value: unknown }>("/admin/settings", {
      key,
      value,
      description,
    }),

  /**
   * Delete a setting.
   */
  deleteSetting: (key: string) =>
    apiClient.delete<{ message: string }>(`/admin/settings/${key}`),

  /**
   * Grant premium to user.
   * @param userId - User ID to grant premium to
   * @param months - Number of months (converted to days)
   */
  grantPremium: (userId: string, months?: number) =>
    apiClient.post<{ message: string }>("/subscriptions/admin/grant-premium", { 
      user_id: userId, 
      days: (months || 1) * 30,
      reason: "Admin grant",
    }),

  /**
   * Revoke premium from user.
   */
  revokePremium: (userId: string) =>
    apiClient.post<{ message: string }>("/subscriptions/admin/revoke-premium", { 
      user_id: userId 
    }),
}

