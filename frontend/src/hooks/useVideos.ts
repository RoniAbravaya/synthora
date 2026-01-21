/**
 * Videos Hooks
 * 
 * React Query hooks for video management.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { videosService } from "@/services/videos"
import toast from "react-hot-toast"
import type { VideoStatus } from "@/types"

export const videoKeys = {
  all: ["videos"] as const,
  list: (params?: { status?: VideoStatus; limit?: number; offset?: number }) =>
    [...videoKeys.all, "list", params] as const,
  detail: (id: string) => [...videoKeys.all, "detail", id] as const,
  status: (id: string) => [...videoKeys.all, "status", id] as const,
  dailyLimit: () => [...videoKeys.all, "daily-limit"] as const,
}

/**
 * Hook to fetch user's videos.
 */
export function useVideos(params?: { status?: VideoStatus; limit?: number; offset?: number }) {
  return useQuery({
    queryKey: videoKeys.list(params),
    queryFn: () => videosService.list(params),
  })
}

/**
 * Hook to fetch a single video.
 */
export function useVideo(id: string) {
  return useQuery({
    queryKey: videoKeys.detail(id),
    queryFn: () => videosService.get(id),
    enabled: !!id,
  })
}

/**
 * Hook to fetch video status with polling.
 */
export function useVideoStatus(id: string, enabled = true) {
  return useQuery({
    queryKey: videoKeys.status(id),
    queryFn: () => videosService.getStatus(id),
    enabled: enabled && !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      // Stop polling when completed or failed
      if (status === "completed" || status === "failed") {
        return false
      }
      return 2000 // Poll every 2 seconds
    },
  })
}

/**
 * Hook to fetch daily generation limit.
 */
export function useDailyLimit() {
  return useQuery({
    queryKey: videoKeys.dailyLimit(),
    queryFn: () => videosService.getDailyLimit(),
  })
}

/**
 * Hook to generate a video.
 */
export function useGenerateVideo() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: videosService.generate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: videoKeys.all })
      toast.success("Video generation started!")
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to start video generation")
    },
  })
}

/**
 * Hook to retry video generation.
 */
export function useRetryVideo() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: videosService.retry,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: videoKeys.all })
      toast.success("Retrying video generation...")
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to retry generation")
    },
  })
}

/**
 * Hook to swap integration for a failed step.
 */
export function useSwapIntegration() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, step, provider }: { id: string; step: string; provider: string }) =>
      videosService.swapIntegration(id, { step, new_provider: provider }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: videoKeys.all })
      toast.success("Integration swapped, retrying...")
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to swap integration")
    },
  })
}

/**
 * Hook to delete a video.
 */
export function useDeleteVideo() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: videosService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: videoKeys.all })
      toast.success("Video deleted")
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to delete video")
    },
  })
}

