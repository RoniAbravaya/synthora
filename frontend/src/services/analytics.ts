/**
 * Analytics API Service
 */

import { apiClient } from "@/lib/api"
import type { TimeSeriesDataPoint, SocialPlatform } from "@/types"

// Response types matching backend schemas
export interface SummaryMetrics {
  views: number
  likes: number
  comments: number
  shares: number
  saves: number
  engagement_rate: number
}

export interface OverviewResponse {
  period_days: number
  total_posts: number
  summary: SummaryMetrics
  by_platform: Record<string, Record<string, number>>
  views_change?: number | null
  likes_change?: number | null
  engagement_change?: number | null
}

export interface PlatformMetrics {
  platform: string
  views: number
  likes: number
  comments: number
  shares: number
  engagement_rate: number
}

export interface PlatformComparisonResponse {
  period_days: number
  platforms: PlatformMetrics[]
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
   * @param days - Number of days to fetch analytics for (default: 30)
   */
  getOverview: (days?: number) =>
    apiClient.get<OverviewResponse>("/analytics/overview", { params: { days: days ?? 30 } }),

  /**
   * Get platform comparison.
   * @param days - Number of days to fetch analytics for (default: 30)
   */
  getPlatformComparison: (days?: number) =>
    apiClient.get<PlatformComparisonResponse>("/analytics/platforms", { params: { days: days ?? 30 } }),

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

