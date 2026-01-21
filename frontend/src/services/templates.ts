/**
 * Templates API Service
 */

import { apiClient } from "@/lib/api"
import type { Template, TemplateConfig } from "@/types"

export interface TemplateListResponse {
  templates: Template[]
  total: number
}

export interface CreateTemplateRequest {
  name: string
  description?: string
  category: string
  is_public?: boolean
  config: TemplateConfig
}

export interface UpdateTemplateRequest {
  name?: string
  description?: string
  category?: string
  is_public?: boolean
  config?: Partial<TemplateConfig>
}

export const templatesService = {
  /**
   * Get all templates (system + user's own).
   */
  list: (params?: { category?: string; is_system?: boolean }) =>
    apiClient.get<TemplateListResponse>("/templates", { params }),

  /**
   * Get a specific template.
   */
  get: (id: string) =>
    apiClient.get<{ template: Template }>(`/templates/${id}`),

  /**
   * Create a new template.
   */
  create: (data: CreateTemplateRequest) =>
    apiClient.post<{ template: Template }>("/templates", data),

  /**
   * Update a template.
   */
  update: (id: string, data: UpdateTemplateRequest) =>
    apiClient.patch<{ template: Template }>(`/templates/${id}`, data),

  /**
   * Delete a template.
   */
  delete: (id: string) =>
    apiClient.delete<{ message: string }>(`/templates/${id}`),

  /**
   * Duplicate a template.
   */
  duplicate: (id: string, name?: string) =>
    apiClient.post<{ template: Template }>(`/templates/${id}/duplicate`, { name }),

  /**
   * Get template categories.
   */
  getCategories: () =>
    apiClient.get<{ categories: string[] }>("/templates/categories"),
}

