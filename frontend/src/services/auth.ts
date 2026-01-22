/**
 * Auth API Service
 */

import { apiClient } from "@/lib/api"
import type { User } from "@/types"

export interface LoginRequest {
  id_token: string
}

export interface LoginResponse {
  user: User
  is_new_user: boolean
  is_first_user: boolean
}

export interface SetupStatusResponse {
  setup_completed: boolean
  has_admin: boolean
}

export const authService = {
  /**
   * Login or register user via Firebase token.
   */
  login: (data: LoginRequest) =>
    apiClient.post<LoginResponse>("/auth/login", data),

  /**
   * Logout current user.
   */
  logout: () =>
    apiClient.post<{ message: string }>("/auth/logout"),

  /**
   * Get current user profile.
   */
  getMe: () =>
    apiClient.get<{ user: User }>("/auth/me"),

  /**
   * Check setup status (first user becomes admin).
   */
  getSetupStatus: () =>
    apiClient.get<SetupStatusResponse>("/auth/setup-status"),

  /**
   * Complete initial setup.
   */
  completeSetup: () =>
    apiClient.post<{ message: string }>("/auth/setup"),

  /**
   * Verify token validity.
   */
  verifyToken: () =>
    apiClient.post<{ valid: boolean; user_id: string }>("/auth/verify-token"),
}

