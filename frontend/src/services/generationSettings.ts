/**
 * Generation Settings API Service
 * 
 * Manages user's video generation preferences including
 * default providers, subtitle styles, and cost estimation.
 */

import { apiClient } from "@/lib/api"

// =============================================================================
// Types
// =============================================================================

export interface ProviderInfo {
  provider: string
  display_name: string
  is_valid: boolean
  estimated_cost: number
}

export interface CategoryProviders {
  script: ProviderInfo[]
  voice: ProviderInfo[]
  media: ProviderInfo[]
  video_ai: ProviderInfo[]
  assembly: ProviderInfo[]
}

export interface SubtitleStyleInfo {
  name: string
  display_name: string
  description: string
  is_default: boolean
  preview: Record<string, unknown>
}

export interface UserGenerationSettings {
  id: string
  user_id: string
  default_script_provider: string | null
  default_voice_provider: string | null
  default_media_provider: string | null
  default_video_ai_provider: string | null
  default_assembly_provider: string | null
  subtitle_style: string
  created_at: string | null
  updated_at: string | null
}

export interface UserGenerationSettingsUpdate {
  default_script_provider?: string | null
  default_voice_provider?: string | null
  default_media_provider?: string | null
  default_video_ai_provider?: string | null
  default_assembly_provider?: string | null
  subtitle_style?: string
}

export interface CostBreakdownItem {
  category: string
  provider: string | null
  provider_name: string
  cost: number
  unit: string
  description: string
}

export interface CostEstimateResponse {
  breakdown: CostBreakdownItem[]
  total_cost: number
  currency: string
  assumptions: string
}

export interface AvailableProvidersResponse {
  providers: CategoryProviders
  subtitle_styles: SubtitleStyleInfo[]
}

export interface EffectiveProvidersResponse {
  script: string | null
  voice: string | null
  media: string | null
  video_ai: string | null
  assembly: string | null
}

export interface SubtitleConfig {
  font_name: string
  font_size: number
  primary_color: string
  background_color: string
  outline_color: string
  outline_width: number
  bold: boolean
  position: string
}

// =============================================================================
// Service
// =============================================================================

export const generationSettingsService = {
  /**
   * Get current user's generation settings.
   */
  get: () =>
    apiClient.get<UserGenerationSettings>("/settings/generation"),

  /**
   * Update user's generation settings.
   */
  update: (settings: UserGenerationSettingsUpdate) =>
    apiClient.put<UserGenerationSettings>("/settings/generation", settings),

  /**
   * Get estimated cost per video based on current settings.
   */
  getCostEstimate: () =>
    apiClient.get<CostEstimateResponse>("/settings/generation/cost-estimate"),

  /**
   * Get available providers for each category.
   */
  getAvailableProviders: () =>
    apiClient.get<AvailableProvidersResponse>("/settings/generation/available-providers"),

  /**
   * Get effective providers (user default or first available).
   */
  getEffectiveProviders: () =>
    apiClient.get<EffectiveProvidersResponse>("/settings/generation/effective-providers"),

  /**
   * Get subtitle style configuration.
   */
  getSubtitleConfig: () =>
    apiClient.get<SubtitleConfig>("/settings/generation/subtitle-config"),
}
