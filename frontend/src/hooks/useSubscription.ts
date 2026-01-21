/**
 * Subscription Hooks
 * 
 * React Query hooks for subscription management.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { subscriptionsService } from "@/services/subscriptions"
import toast from "react-hot-toast"

export const subscriptionKeys = {
  all: ["subscription"] as const,
  plans: () => [...subscriptionKeys.all, "plans"] as const,
  status: () => [...subscriptionKeys.all, "status"] as const,
  details: () => [...subscriptionKeys.all, "details"] as const,
  invoices: () => [...subscriptionKeys.all, "invoices"] as const,
}

/**
 * Hook to fetch available plans.
 */
export function usePlans() {
  return useQuery({
    queryKey: subscriptionKeys.plans(),
    queryFn: () => subscriptionsService.getPlans(),
  })
}

/**
 * Hook to fetch subscription status.
 */
export function useSubscriptionStatus() {
  return useQuery({
    queryKey: subscriptionKeys.status(),
    queryFn: () => subscriptionsService.getStatus(),
  })
}

/**
 * Hook to fetch subscription details.
 */
export function useSubscriptionDetails() {
  return useQuery({
    queryKey: subscriptionKeys.details(),
    queryFn: () => subscriptionsService.getDetails(),
  })
}

/**
 * Hook to fetch invoices.
 */
export function useInvoices() {
  return useQuery({
    queryKey: subscriptionKeys.invoices(),
    queryFn: () => subscriptionsService.getInvoices(),
  })
}

/**
 * Hook to create checkout session.
 */
export function useCreateCheckout() {
  return useMutation({
    mutationFn: subscriptionsService.createCheckout,
    onSuccess: (data) => {
      // Redirect to Stripe checkout
      window.location.href = data.checkout_url
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to start checkout")
    },
  })
}

/**
 * Hook to create customer portal session.
 */
export function useCreatePortal() {
  return useMutation({
    mutationFn: subscriptionsService.createPortal,
    onSuccess: (data) => {
      // Redirect to Stripe portal
      window.location.href = data.portal_url
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to open billing portal")
    },
  })
}

/**
 * Hook to cancel subscription.
 */
export function useCancelSubscription() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: subscriptionsService.cancel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: subscriptionKeys.all })
      toast.success("Subscription will be canceled at the end of the billing period")
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to cancel subscription")
    },
  })
}

/**
 * Hook to reactivate subscription.
 */
export function useReactivateSubscription() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: subscriptionsService.reactivate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: subscriptionKeys.all })
      toast.success("Subscription reactivated!")
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to reactivate subscription")
    },
  })
}

/**
 * Hook to change subscription plan.
 */
export function useChangePlan() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: subscriptionsService.changePlan,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: subscriptionKeys.all })
      toast.success("Plan changed successfully!")
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to change plan")
    },
  })
}

