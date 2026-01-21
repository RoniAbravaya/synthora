/**
 * Social Accounts API Service
 */

import { apiClient } from "@/lib/api"
import type { SocialAccount, SocialPlatform } from "@/types"

export interface SocialAccountListResponse {
  accounts: SocialAccount[]
  total: number
}

export interface OAuthInitResponse {
  authorization_url: string
  state: string
  platform: string
}

export interface OAuthCallbackResponse {
  account: SocialAccount
  message: string
}

export const socialAccountsService = {
  /**
   * Get connected social accounts.
   */
  list: () =>
    apiClient.get<SocialAccountListResponse>("/social-accounts"),

  /**
   * Get a specific account.
   */
  get: (id: string) =>
    apiClient.get<{ account: SocialAccount }>(`/social-accounts/${id}`),

  /**
   * Initiate OAuth flow for a platform.
   */
  initiateOAuth: (platform: SocialPlatform) =>
    apiClient.post<OAuthInitResponse>(`/social-accounts/connect/${platform}`),

  /**
   * Complete OAuth callback.
   */
  completeOAuth: (platform: SocialPlatform, code: string, state: string) =>
    apiClient.post<OAuthCallbackResponse>(`/social-accounts/oauth/${platform}/callback`, {
      code,
      state,
    }),

  /**
   * Disconnect a social account.
   */
  disconnect: (id: string) =>
    apiClient.delete<{ message: string }>(`/social-accounts/${id}`),

  /**
   * Refresh account token.
   */
  refreshToken: (id: string) =>
    apiClient.post<{ account: SocialAccount }>(`/social-accounts/${id}/refresh`),

  /**
   * Check if account token is valid.
   */
  checkStatus: (id: string) =>
    apiClient.get<{ is_valid: boolean; expires_at: string | null }>(
      `/social-accounts/${id}/status`
    ),
}

