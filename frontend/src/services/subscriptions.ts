/**
 * Subscriptions API Service
 */

import { apiClient } from "@/lib/api"
import type { Subscription, SubscriptionPlan, PlanInfo } from "@/types"

export interface PlansResponse {
  plans: PlanInfo[]
}

export interface SubscriptionStatusResponse {
  has_subscription: boolean
  subscription: Subscription | null
  is_premium: boolean
}

export interface CheckoutResponse {
  checkout_url: string
  session_id: string
}

export interface PortalResponse {
  portal_url: string
}

export interface Invoice {
  id: string
  amount: number
  status: string
  created_at: string
  invoice_url: string
}

export interface InvoicesResponse {
  invoices: Invoice[]
}

export const subscriptionsService = {
  /**
   * Get available plans.
   */
  getPlans: () =>
    apiClient.get<PlansResponse>("/subscriptions/plans"),

  /**
   * Get current subscription status.
   */
  getStatus: () =>
    apiClient.get<SubscriptionStatusResponse>("/subscriptions/status"),

  /**
   * Get subscription details.
   */
  getDetails: () =>
    apiClient.get<{ subscription: Subscription }>("/subscriptions/details"),

  /**
   * Create checkout session.
   */
  createCheckout: (plan: SubscriptionPlan) =>
    apiClient.post<CheckoutResponse>("/subscriptions/checkout", { plan }),

  /**
   * Create customer portal session.
   */
  createPortal: () =>
    apiClient.post<PortalResponse>("/subscriptions/portal"),

  /**
   * Cancel subscription.
   */
  cancel: () =>
    apiClient.post<{ message: string; subscription: Subscription }>("/subscriptions/cancel"),

  /**
   * Reactivate canceled subscription.
   */
  reactivate: () =>
    apiClient.post<{ message: string; subscription: Subscription }>("/subscriptions/reactivate"),

  /**
   * Change subscription plan.
   */
  changePlan: (plan: SubscriptionPlan) =>
    apiClient.post<{ message: string; subscription: Subscription }>("/subscriptions/change-plan", { plan }),

  /**
   * Get invoices.
   */
  getInvoices: () =>
    apiClient.get<InvoicesResponse>("/subscriptions/invoices"),
}

