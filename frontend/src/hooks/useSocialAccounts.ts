/**
 * Social Accounts Hooks
 * 
 * React Query hooks for social account management.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { socialAccountsService } from "@/services/socialAccounts"
import toast from "react-hot-toast"
import type { SocialPlatform } from "@/types"

export const socialAccountKeys = {
  all: ["social-accounts"] as const,
  list: () => [...socialAccountKeys.all, "list"] as const,
  detail: (id: string) => [...socialAccountKeys.all, "detail", id] as const,
}

/**
 * Hook to fetch connected social accounts.
 */
export function useSocialAccounts() {
  return useQuery({
    queryKey: socialAccountKeys.list(),
    queryFn: () => socialAccountsService.list(),
  })
}

/**
 * Hook to fetch a single social account.
 */
export function useSocialAccount(id: string) {
  return useQuery({
    queryKey: socialAccountKeys.detail(id),
    queryFn: () => socialAccountsService.get(id),
    enabled: !!id,
  })
}

/**
 * Platforms that use Firebase OAuth (Google-based).
 */
const FIREBASE_OAUTH_PLATFORMS: SocialPlatform[] = ["youtube"]

/**
 * Hook to connect a social account.
 * Uses Firebase OAuth for Google-based platforms (YouTube),
 * and redirect-based OAuth for others (TikTok, Instagram, Facebook).
 */
export function useConnectAccount() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (platform: SocialPlatform) => {
      if (FIREBASE_OAUTH_PLATFORMS.includes(platform)) {
        // Use Firebase OAuth (popup-based)
        return socialAccountsService.connectWithFirebase(platform)
      } else {
        // Use redirect-based OAuth
        const result = await socialAccountsService.initiateOAuth(platform)
        window.location.href = result.authorization_url
        // This will redirect, so we won't return
        return new Promise(() => {}) // Never resolves
      }
    },
    onSuccess: (data) => {
      if (data && data.account) {
        queryClient.invalidateQueries({ queryKey: socialAccountKeys.all })
        toast.success(`${data.account.platform} account connected!`)
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to connect account")
    },
  })
}

/**
 * Hook to initiate OAuth flow (legacy - use useConnectAccount instead).
 * @deprecated Use useConnectAccount for a unified experience
 */
export function useInitiateOAuth() {
  return useMutation({
    mutationFn: (platform: SocialPlatform) => socialAccountsService.initiateOAuth(platform),
    onSuccess: (data) => {
      // Redirect to OAuth provider
      window.location.href = data.authorization_url
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to start authentication")
    },
  })
}

/**
 * Hook to disconnect a social account.
 */
export function useDisconnectAccount() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: socialAccountsService.disconnect,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: socialAccountKeys.all })
      toast.success("Account disconnected")
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to disconnect account")
    },
  })
}

/**
 * Hook to refresh account token.
 */
export function useRefreshToken() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: socialAccountsService.refreshToken,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: socialAccountKeys.all })
      toast.success("Token refreshed")
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to refresh token")
    },
  })
}

