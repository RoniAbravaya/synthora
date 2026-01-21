/**
 * Integrations API Service
 */

import { apiClient } from "@/lib/api"
import type { Integration, AvailableIntegration, IntegrationCategory } from "@/types"

export interface IntegrationListResponse {
  integrations: Integration[]
  total: number
}

export interface AvailableIntegrationsResponse {
  integrations: AvailableIntegration[]
  categories: {
    name: IntegrationCategory
    display_name: string
    description: string
    required_count: number
  }[]
}

export interface AddIntegrationRequest {
  provider: string
  api_key: string
}

export interface UpdateIntegrationRequest {
  api_key?: string
  is_active?: boolean
}

export interface ValidationResult {
  is_valid: boolean
  message: string
  details?: Record<string, unknown>
}

export interface RevealKeyResponse {
  api_key: string
}

export interface ReadinessResponse {
  ready: boolean
  missing_categories: IntegrationCategory[]
  configured_categories: IntegrationCategory[]
}

export const integrationsService = {
  /**
   * Get user's configured integrations.
   */
  list: () =>
    apiClient.get<IntegrationListResponse>("/integrations"),

  /**
   * Get available integrations to configure.
   */
  getAvailable: () =>
    apiClient.get<AvailableIntegrationsResponse>("/integrations/available"),

  /**
   * Add a new integration.
   */
  add: (data: AddIntegrationRequest) =>
    apiClient.post<{ integration: Integration; validation: ValidationResult }>(
      "/integrations",
      data
    ),

  /**
   * Update an integration.
   */
  update: (id: string, data: UpdateIntegrationRequest) =>
    apiClient.patch<{ integration: Integration }>(`/integrations/${id}`, data),

  /**
   * Delete an integration.
   */
  delete: (id: string) =>
    apiClient.delete<{ message: string }>(`/integrations/${id}`),

  /**
   * Validate an integration's API key.
   */
  validate: (id: string) =>
    apiClient.post<ValidationResult>(`/integrations/${id}/validate`),

  /**
   * Reveal full API key (requires auth).
   */
  revealKey: (id: string) =>
    apiClient.get<RevealKeyResponse>(`/integrations/${id}/reveal`),

  /**
   * Toggle integration active status.
   */
  toggle: (id: string, isActive: boolean) =>
    apiClient.patch<{ integration: Integration }>(`/integrations/${id}/toggle`, {
      is_active: isActive,
    }),

  /**
   * Check if user has minimum required integrations.
   */
  checkReadiness: () =>
    apiClient.get<ReadinessResponse>("/integrations/readiness"),
}

