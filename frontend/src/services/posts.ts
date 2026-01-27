/**
 * Posts API Service
 */

import { apiClient } from "@/lib/api"
import type { Post, PostCreate, PostStatus, SocialPlatform } from "@/types"

export interface PostListResponse {
  posts: Post[]
  total: number
  limit: number
  offset: number
  has_more: boolean
}

export interface CalendarPost {
  id: string
  title: string
  platforms: SocialPlatform[]
  scheduled_at: string
  status: PostStatus
}

export interface CalendarResponse {
  posts: CalendarPost[]
  month: number
  year: number
}

export interface PostUpdateRequest {
  title?: string
  description?: string
  platforms?: SocialPlatform[]
  scheduled_at?: string | null
  platform_overrides?: Record<string, { title?: string; description?: string }>
}

export const postsService = {
  /**
   * Get user's posts.
   */
  list: (params?: { status?: PostStatus; platform?: SocialPlatform; limit?: number; offset?: number }) =>
    apiClient.get<PostListResponse>("/posts", { params }),

  /**
   * Get a specific post.
   */
  get: (id: string) =>
    apiClient.get<{ post: Post }>(`/posts/${id}`),

  /**
   * Create a new post.
   */
  create: (data: PostCreate) =>
    apiClient.post<{ post: Post }>("/posts", data),

  /**
   * Update a post.
   */
  update: (id: string, data: PostUpdateRequest) =>
    apiClient.patch<{ post: Post }>(`/posts/${id}`, data),

  /**
   * Delete a post.
   */
  delete: (id: string) =>
    apiClient.delete<{ message: string }>(`/posts/${id}`),

  /**
   * Publish a post immediately.
   */
  publish: (id: string) =>
    apiClient.post<{ post: Post; results: Record<string, { success: boolean; url?: string; error?: string }> }>(
      `/posts/${id}/publish`
    ),

  /**
   * Publish a post now (alias for publish).
   */
  publishNow: (id: string) =>
    apiClient.post<{ post: Post }>(`/posts/${id}/publish`),

  /**
   * Get calendar view of scheduled posts.
   */
  getCalendar: (year: number, month: number) =>
    apiClient.get<CalendarResponse>(`/posts/calendar/${year}/${month}`),

  /**
   * Get upcoming scheduled posts.
   */
  getUpcoming: (limit?: number) =>
    apiClient.get<PostListResponse>("/posts/upcoming", { params: { limit } }),
}

