/**
 * Social Accounts API Service
 * 
 * Handles social media account connections via server-side OAuth.
 * Uses redirect-based OAuth flow to ensure we get refresh tokens for long-term access.
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
   * Uses server-side redirect-based OAuth to get both access and refresh tokens.
   * 
   * @param platform - The platform to connect (youtube, tiktok, instagram, facebook)
   * @returns Authorization URL to redirect the user to
   */
  initiateOAuth: (platform: SocialPlatform) =>
    apiClient.post<OAuthInitResponse>(`/social-accounts/connect/${platform}`),

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

