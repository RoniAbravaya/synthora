/**
 * Social Accounts API Service
 * 
 * Handles social media account connections via Firebase OAuth.
 */

import { apiClient } from "@/lib/api"
import { connectYouTubeAccount, type SocialOAuthResult } from "@/lib/firebase"
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

export interface FirebaseConnectRequest {
  access_token: string
  platform_user_id: string
  email: string | null
  display_name: string | null
  photo_url: string | null
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
   * Connect a social account using Firebase OAuth.
   * This is the preferred method for Google-based platforms (YouTube).
   * 
   * @param platform - The platform to connect
   * @returns Connected account details
   */
  connectWithFirebase: async (platform: SocialPlatform): Promise<OAuthCallbackResponse> => {
    let oauthResult: SocialOAuthResult
    
    // Use Firebase OAuth based on platform
    switch (platform) {
      case "youtube":
        oauthResult = await connectYouTubeAccount()
        break
      default:
        throw new Error(`Firebase OAuth not supported for ${platform}. Use initiateOAuth instead.`)
    }
    
    // Send the token to backend to create the social account
    const response = await apiClient.post<OAuthCallbackResponse>(
      `/social-accounts/connect/${platform}/firebase`,
      {
        access_token: oauthResult.accessToken,
        platform_user_id: oauthResult.platformUserId,
        email: oauthResult.email,
        display_name: oauthResult.displayName,
        photo_url: oauthResult.photoUrl,
      } as FirebaseConnectRequest
    )
    
    return response
  },

  /**
   * Initiate OAuth flow for a platform (legacy redirect-based).
   * Use connectWithFirebase for Google-based platforms like YouTube.
   */
  initiateOAuth: (platform: SocialPlatform) =>
    apiClient.post<OAuthInitResponse>(`/social-accounts/connect/${platform}`),

  /**
   * Complete OAuth callback (legacy).
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

