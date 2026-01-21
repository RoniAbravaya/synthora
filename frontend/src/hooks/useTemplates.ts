/**
 * Templates Hooks
 * 
 * React Query hooks for template management.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { templatesService } from "@/services/templates"
import toast from "react-hot-toast"

export const templateKeys = {
  all: ["templates"] as const,
  list: (params?: { category?: string; is_system?: boolean }) =>
    [...templateKeys.all, "list", params] as const,
  detail: (id: string) => [...templateKeys.all, "detail", id] as const,
  categories: () => [...templateKeys.all, "categories"] as const,
}

/**
 * Hook to fetch templates.
 */
export function useTemplates(params?: { category?: string; is_system?: boolean }) {
  return useQuery({
    queryKey: templateKeys.list(params),
    queryFn: () => templatesService.list(params),
  })
}

/**
 * Hook to fetch a single template.
 */
export function useTemplate(id: string) {
  return useQuery({
    queryKey: templateKeys.detail(id),
    queryFn: () => templatesService.get(id),
    enabled: !!id,
  })
}

/**
 * Hook to fetch template categories.
 */
export function useTemplateCategories() {
  return useQuery({
    queryKey: templateKeys.categories(),
    queryFn: () => templatesService.getCategories(),
  })
}

/**
 * Hook to create a template.
 */
export function useCreateTemplate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: templatesService.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: templateKeys.all })
      toast.success("Template created!")
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to create template")
    },
  })
}

/**
 * Hook to update a template.
 */
export function useUpdateTemplate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof templatesService.update>[1] }) =>
      templatesService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: templateKeys.all })
      toast.success("Template updated!")
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to update template")
    },
  })
}

/**
 * Hook to delete a template.
 */
export function useDeleteTemplate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: templatesService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: templateKeys.all })
      toast.success("Template deleted")
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to delete template")
    },
  })
}

/**
 * Hook to duplicate a template.
 */
export function useDuplicateTemplate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, name }: { id: string; name?: string }) =>
      templatesService.duplicate(id, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: templateKeys.all })
      toast.success("Template duplicated!")
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to duplicate template")
    },
  })
}

