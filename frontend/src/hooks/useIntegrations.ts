/**
 * Integrations Hooks
 * 
 * React Query hooks for integration management.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { integrationsService } from "@/services/integrations"
import toast from "react-hot-toast"

export const integrationKeys = {
  all: ["integrations"] as const,
  list: () => [...integrationKeys.all, "list"] as const,
  available: () => [...integrationKeys.all, "available"] as const,
  readiness: () => [...integrationKeys.all, "readiness"] as const,
}

/**
 * Hook to fetch user's integrations.
 */
export function useIntegrations() {
  return useQuery({
    queryKey: integrationKeys.list(),
    queryFn: () => integrationsService.list(),
  })
}

/**
 * Hook to fetch available integrations.
 */
export function useAvailableIntegrations() {
  return useQuery({
    queryKey: integrationKeys.available(),
    queryFn: () => integrationsService.getAvailable(),
  })
}

/**
 * Hook to check integration readiness.
 */
export function useIntegrationReadiness() {
  return useQuery({
    queryKey: integrationKeys.readiness(),
    queryFn: () => integrationsService.checkReadiness(),
  })
}

/**
 * Hook to add an integration.
 */
export function useAddIntegration() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: integrationsService.add,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: integrationKeys.all })
      if (data.validation.is_valid) {
        toast.success("Integration added successfully!")
      } else {
        toast.error(`Integration added but validation failed: ${data.validation.message}`)
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to add integration")
    },
  })
}

/**
 * Hook to update an integration.
 */
export function useUpdateIntegration() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof integrationsService.update>[1] }) =>
      integrationsService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: integrationKeys.all })
      toast.success("Integration updated!")
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to update integration")
    },
  })
}

/**
 * Hook to delete an integration.
 */
export function useDeleteIntegration() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: integrationsService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: integrationKeys.all })
      toast.success("Integration removed")
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to remove integration")
    },
  })
}

/**
 * Hook to validate an integration.
 */
export function useValidateIntegration() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: integrationsService.validate,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: integrationKeys.all })
      if (data.is_valid) {
        toast.success("API key is valid!")
      } else {
        toast.error(`Validation failed: ${data.message}`)
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to validate integration")
    },
  })
}

/**
 * Hook to toggle integration status.
 */
export function useToggleIntegration() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      integrationsService.toggle(id, isActive),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: integrationKeys.all })
      const status = data.integration.is_active ? "enabled" : "disabled"
      toast.success(`Integration ${status}`)
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to toggle integration")
    },
  })
}

