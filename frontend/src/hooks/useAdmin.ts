/**
 * Admin Hooks
 * 
 * React Query hooks for admin functionality including
 * platform stats, user management, and settings.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { adminService, type PlatformStats, type ActivityStats, type TopUser, type AdminUserListResponse, type AdminUserDetailResponse } from "@/services/admin"
import type { UserRole } from "@/types"

// =============================================================================
// Types
// =============================================================================

export interface UserListFilters {
  search?: string
  role?: UserRole
  is_active?: boolean
  sort_by?: string
  sort_order?: "asc" | "desc"
  limit?: number
  offset?: number
}

// =============================================================================
// Query Keys
// =============================================================================

export const adminKeys = {
  all: ["admin"] as const,
  stats: () => [...adminKeys.all, "stats"] as const,
  activityStats: (days?: number) => [...adminKeys.all, "activity", days] as const,
  topUsers: (metric?: string, limit?: number) => [...adminKeys.all, "topUsers", metric, limit] as const,
  users: (filters?: UserListFilters) => [...adminKeys.all, "users", filters] as const,
  user: (userId: string) => [...adminKeys.all, "user", userId] as const,
  settings: () => [...adminKeys.all, "settings"] as const,
  setting: (key: string) => [...adminKeys.all, "setting", key] as const,
}

// =============================================================================
// Platform Stats Hooks
// =============================================================================

/**
 * Hook to fetch platform-wide statistics.
 */
export function useAdminStats() {
  return useQuery({
    queryKey: adminKeys.stats(),
    queryFn: () => adminService.getStats(),
    staleTime: 60 * 1000, // 1 minute
  })
}

/**
 * Hook to fetch activity statistics over time.
 */
export function useAdminActivityStats(days: number = 30) {
  return useQuery({
    queryKey: adminKeys.activityStats(days),
    queryFn: () => adminService.getActivityStats(days),
    staleTime: 60 * 1000,
  })
}

/**
 * Hook to fetch top users by metric.
 */
export function useAdminTopUsers(metric: "videos" | "posts" = "videos", limit: number = 10) {
  return useQuery({
    queryKey: adminKeys.topUsers(metric, limit),
    queryFn: () => adminService.getTopUsers(metric, limit),
    staleTime: 60 * 1000,
  })
}

// =============================================================================
// User Management Hooks
// =============================================================================

/**
 * Hook to fetch users with filters.
 */
export function useAdminUsers(filters: UserListFilters = {}) {
  return useQuery({
    queryKey: adminKeys.users(filters),
    queryFn: () => adminService.listUsers(filters),
    staleTime: 30 * 1000,
  })
}

/**
 * Hook to fetch a single user's details.
 */
export function useAdminUserDetails(userId: string | null) {
  return useQuery({
    queryKey: adminKeys.user(userId || ""),
    queryFn: () => adminService.getUserDetails(userId!),
    enabled: !!userId,
    staleTime: 30 * 1000,
  })
}

/**
 * Hook to update a user's role.
 */
export function useUpdateUserRole() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: UserRole }) =>
      adminService.updateUserRole(userId, role),
    onSuccess: (_, { userId }) => {
      queryClient.invalidateQueries({ queryKey: adminKeys.users() })
      queryClient.invalidateQueries({ queryKey: adminKeys.user(userId) })
      queryClient.invalidateQueries({ queryKey: adminKeys.stats() })
    },
  })
}

/**
 * Hook to update a user's status.
 */
export function useUpdateUserStatus() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ userId, isActive }: { userId: string; isActive: boolean }) =>
      adminService.updateUserStatus(userId, isActive),
    onSuccess: (_, { userId }) => {
      queryClient.invalidateQueries({ queryKey: adminKeys.users() })
      queryClient.invalidateQueries({ queryKey: adminKeys.user(userId) })
      queryClient.invalidateQueries({ queryKey: adminKeys.stats() })
    },
  })
}

/**
 * Hook to delete a user.
 */
export function useDeleteUser() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ userId, hardDelete }: { userId: string; hardDelete?: boolean }) =>
      adminService.deleteUser(userId, hardDelete),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.users() })
      queryClient.invalidateQueries({ queryKey: adminKeys.stats() })
    },
  })
}

/**
 * Hook to grant premium to a user.
 */
export function useGrantPremium() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ userId, months }: { userId: string; months?: number }) =>
      adminService.grantPremium(userId, months),
    onSuccess: (_, { userId }) => {
      queryClient.invalidateQueries({ queryKey: adminKeys.users() })
      queryClient.invalidateQueries({ queryKey: adminKeys.user(userId) })
      queryClient.invalidateQueries({ queryKey: adminKeys.stats() })
    },
  })
}

/**
 * Hook to revoke premium from a user.
 */
export function useRevokePremium() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (userId: string) => adminService.revokePremium(userId),
    onSuccess: (_, userId) => {
      queryClient.invalidateQueries({ queryKey: adminKeys.users() })
      queryClient.invalidateQueries({ queryKey: adminKeys.user(userId) })
      queryClient.invalidateQueries({ queryKey: adminKeys.stats() })
    },
  })
}

// =============================================================================
// Settings Hooks
// =============================================================================

/**
 * Hook to fetch all settings.
 */
export function useAdminSettings() {
  return useQuery({
    queryKey: adminKeys.settings(),
    queryFn: () => adminService.getSettings(),
    staleTime: 60 * 1000,
  })
}

/**
 * Hook to fetch a single setting.
 */
export function useAdminSetting(key: string) {
  return useQuery({
    queryKey: adminKeys.setting(key),
    queryFn: () => adminService.getSetting(key),
    enabled: !!key,
    staleTime: 60 * 1000,
  })
}

/**
 * Hook to set a setting.
 */
export function useSetSetting() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ key, value, description }: { key: string; value: unknown; description?: string }) =>
      adminService.setSetting(key, value, description),
    onSuccess: (_, { key }) => {
      queryClient.invalidateQueries({ queryKey: adminKeys.settings() })
      queryClient.invalidateQueries({ queryKey: adminKeys.setting(key) })
    },
  })
}

/**
 * Hook to delete a setting.
 */
export function useDeleteSetting() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (key: string) => adminService.deleteSetting(key),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.settings() })
    },
  })
}
