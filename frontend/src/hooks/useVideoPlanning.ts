/**
 * Video Planning Hooks
 *
 * React Query hooks for video scheduling and content planning.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  videoPlanningService,
  type UpdatePlannedVideoRequest,
  type CreateMonthlyPlanRequest,
} from "@/services/videoPlanning"
import type { ScheduleVideoRequest, CreateSeriesRequest } from "@/types"

// =============================================================================
// Query Keys
// =============================================================================

export const videoPlanningKeys = {
  all: ["video-planning"] as const,
  planned: (options?: Record<string, unknown>) =>
    [...videoPlanningKeys.all, "planned", options] as const,
  calendar: (startDate: string, endDate: string) =>
    [...videoPlanningKeys.all, "calendar", startDate, endDate] as const,
}

// =============================================================================
// Query Hooks
// =============================================================================

/**
 * Hook to get all planned videos.
 */
export function usePlannedVideos(options?: {
  status_filter?: string
  series_name?: string
  include_posted?: boolean
}) {
  return useQuery({
    queryKey: videoPlanningKeys.planned(options),
    queryFn: () => videoPlanningService.getPlannedVideos(options),
    staleTime: 30 * 1000,
  })
}

/**
 * Hook to get calendar view of planned videos.
 */
export function useCalendarView(startDate: string, endDate: string, enabled = true) {
  return useQuery({
    queryKey: videoPlanningKeys.calendar(startDate, endDate),
    queryFn: () => videoPlanningService.getCalendarView(startDate, endDate),
    enabled,
    staleTime: 60 * 1000,
  })
}

// =============================================================================
// Mutation Hooks
// =============================================================================

/**
 * Hook to schedule a single video.
 */
export function useScheduleVideo() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: ScheduleVideoRequest) =>
      videoPlanningService.scheduleVideo(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: videoPlanningKeys.all })
    },
  })
}

/**
 * Hook to create a video series.
 */
export function useCreateSeries() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: CreateSeriesRequest) =>
      videoPlanningService.createSeries(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: videoPlanningKeys.all })
    },
  })
}

/**
 * Hook to create a monthly content plan.
 */
export function useCreateMonthlyPlan() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: CreateMonthlyPlanRequest) =>
      videoPlanningService.createMonthlyPlan(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: videoPlanningKeys.all })
    },
  })
}

/**
 * Hook to update a planned video.
 */
export function useUpdatePlannedVideo() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      videoId,
      updates,
    }: {
      videoId: string
      updates: UpdatePlannedVideoRequest
    }) => videoPlanningService.updatePlannedVideo(videoId, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: videoPlanningKeys.all })
    },
  })
}

/**
 * Hook to delete a planned video.
 */
export function useDeletePlannedVideo() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (videoId: string) => videoPlanningService.deletePlannedVideo(videoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: videoPlanningKeys.all })
    },
  })
}

/**
 * Hook to trigger immediate generation for a planned video.
 */
export function useTriggerGeneration() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (videoId: string) => videoPlanningService.triggerGeneration(videoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: videoPlanningKeys.all })
    },
  })
}
