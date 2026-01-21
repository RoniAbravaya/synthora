/**
 * Analytics API Service
 */

import { apiClient } from "@/lib/api"
import type { AnalyticsOverview, AnalyticsMetrics, TimeSeriesDataPoint, SocialPlatform } from "@/types"

export interface OverviewResponse {
  overview: AnalyticsOverview
  period: string
}

export interface PlatformComparisonResponse {
  platforms: Record<SocialPlatform, AnalyticsMetrics>
  best_performing: SocialPlatform | null
}

export interface TimeSeriesResponse {
  metric: string
  data: TimeSeriesDataPoint[]
  period: string
}

export interface TopPerformingItem {
  post_id: string
  video_id: string
  title: string
  platform: SocialPlatform
  views: number
  likes: number
  engagement_rate: number
  thumbnail_url: string | null
}

export interface TopPerformingResponse {
  items: TopPerformingItem[]
  metric: string
}

export interface HeatmapCell {
  day: number  // 0-6 (Sunday-Saturday)
  hour: number // 0-23
  value: number
}

export interface HeatmapResponse {
  data: HeatmapCell[]
  metric: string
}

export interface PostAnalyticsResponse {
  post_id: string
  metrics: AnalyticsMetrics
  history: TimeSeriesDataPoint[]
  platform_breakdown: Record<SocialPlatform, AnalyticsMetrics>
}

export const analyticsService = {
  /**
   * Get dashboard overview.
   */
  getOverview: (period?: "7d" | "30d" | "90d") =>
    apiClient.get<OverviewResponse>("/analytics/overview", { params: { period } }),

  /**
   * Get platform comparison.
   */
  getPlatformComparison: (period?: "7d" | "30d" | "90d") =>
    apiClient.get<PlatformComparisonResponse>("/analytics/platforms", { params: { period } }),

  /**
   * Get time series data for a metric.
   */
  getTimeSeries: (metric: string, period?: "7d" | "30d" | "90d") =>
    apiClient.get<TimeSeriesResponse>("/analytics/time-series", { params: { metric, period } }),

  /**
   * Get top performing content.
   */
  getTopPerforming: (metric?: "views" | "likes" | "engagement", limit?: number) =>
    apiClient.get<TopPerformingResponse>("/analytics/top-performing", { params: { metric, limit } }),

  /**
   * Get posting heatmap.
   */
  getHeatmap: (metric?: "views" | "engagement") =>
    apiClient.get<HeatmapResponse>("/analytics/heatmap", { params: { metric } }),

  /**
   * Get analytics for a specific post.
   */
  getPostAnalytics: (postId: string) =>
    apiClient.get<PostAnalyticsResponse>(`/analytics/posts/${postId}`),

  /**
   * Trigger manual analytics sync.
   */
  sync: () =>
    apiClient.post<{ message: string; job_id: string }>("/analytics/sync"),
}

