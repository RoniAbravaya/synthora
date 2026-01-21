/**
 * Application Router
 * 
 * Defines all routes and lazy-loaded pages.
 */

import React, { Suspense, lazy } from "react"
import { createBrowserRouter, Navigate, Outlet } from "react-router-dom"
import { useAuth } from "@/contexts/AuthContext"

// =============================================================================
// Layouts
// =============================================================================

const DashboardLayout = lazy(() => import("@/layouts/DashboardLayout"))
const AuthLayout = lazy(() => import("@/layouts/AuthLayout"))

// =============================================================================
// Pages
// =============================================================================

// Auth Pages
const LoginPage = lazy(() => import("@/pages/auth/LoginPage"))
const SetupPage = lazy(() => import("@/pages/auth/SetupPage"))

// Dashboard Pages
const DashboardPage = lazy(() => import("@/pages/dashboard/DashboardPage"))
const CreateVideoPage = lazy(() => import("@/pages/dashboard/CreateVideoPage"))
const VideosPage = lazy(() => import("@/pages/dashboard/VideosPage"))
const VideoDetailPage = lazy(() => import("@/pages/dashboard/VideoDetailPage"))
const TemplatesPage = lazy(() => import("@/pages/dashboard/TemplatesPage"))
const PostsPage = lazy(() => import("@/pages/dashboard/PostsPage"))
const CalendarPage = lazy(() => import("@/pages/dashboard/CalendarPage"))
const AnalyticsPage = lazy(() => import("@/pages/dashboard/AnalyticsPage"))
const IntegrationsPage = lazy(() => import("@/pages/dashboard/IntegrationsPage"))
const SocialAccountsPage = lazy(() => import("@/pages/dashboard/SocialAccountsPage"))
const SettingsPage = lazy(() => import("@/pages/dashboard/SettingsPage"))
const SuggestionsPage = lazy(() => import("@/pages/dashboard/SuggestionsPage"))

// Admin Pages
const AdminDashboardPage = lazy(() => import("@/pages/admin/AdminDashboardPage"))
const AdminUsersPage = lazy(() => import("@/pages/admin/AdminUsersPage"))
const AdminSettingsPage = lazy(() => import("@/pages/admin/AdminSettingsPage"))

// Error Pages
const NotFoundPage = lazy(() => import("@/pages/errors/NotFoundPage"))

// =============================================================================
// Loading Fallback
// =============================================================================

function PageLoader() {
  return (
    <div className="flex h-screen w-full items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="h-12 w-12 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        <p className="text-muted-foreground">Loading...</p>
      </div>
    </div>
  )
}

// =============================================================================
// Route Guards
// =============================================================================

/**
 * Requires authentication to access child routes.
 */
function RequireAuth() {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return <PageLoader />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}

/**
 * Requires admin role to access child routes.
 */
function RequireAdmin() {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return <PageLoader />
  }

  if (user?.role !== "admin") {
    return <Navigate to="/dashboard" replace />
  }

  return <Outlet />
}

/**
 * Redirects authenticated users away from auth pages.
 */
function RedirectIfAuth() {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return <PageLoader />
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  return <Outlet />
}

// =============================================================================
// Router
// =============================================================================

export const router = createBrowserRouter([
  // Public routes
  {
    path: "/",
    element: <Navigate to="/login" replace />,
  },

  // Auth routes (redirect if already authenticated)
  {
    element: <RedirectIfAuth />,
    children: [
      {
        element: (
          <Suspense fallback={<PageLoader />}>
            <AuthLayout />
          </Suspense>
        ),
        children: [
          {
            path: "/login",
            element: (
              <Suspense fallback={<PageLoader />}>
                <LoginPage />
              </Suspense>
            ),
          },
          {
            path: "/setup",
            element: (
              <Suspense fallback={<PageLoader />}>
                <SetupPage />
              </Suspense>
            ),
          },
        ],
      },
    ],
  },

  // Protected dashboard routes
  {
    element: <RequireAuth />,
    children: [
      {
        element: (
          <Suspense fallback={<PageLoader />}>
            <DashboardLayout />
          </Suspense>
        ),
        children: [
          {
            path: "/dashboard",
            element: (
              <Suspense fallback={<PageLoader />}>
                <DashboardPage />
              </Suspense>
            ),
          },
          {
            path: "/create",
            element: (
              <Suspense fallback={<PageLoader />}>
                <CreateVideoPage />
              </Suspense>
            ),
          },
          {
            path: "/videos",
            element: (
              <Suspense fallback={<PageLoader />}>
                <VideosPage />
              </Suspense>
            ),
          },
          {
            path: "/videos/:id",
            element: (
              <Suspense fallback={<PageLoader />}>
                <VideoDetailPage />
              </Suspense>
            ),
          },
          {
            path: "/templates",
            element: (
              <Suspense fallback={<PageLoader />}>
                <TemplatesPage />
              </Suspense>
            ),
          },
          {
            path: "/posts",
            element: (
              <Suspense fallback={<PageLoader />}>
                <PostsPage />
              </Suspense>
            ),
          },
          {
            path: "/calendar",
            element: (
              <Suspense fallback={<PageLoader />}>
                <CalendarPage />
              </Suspense>
            ),
          },
          {
            path: "/analytics",
            element: (
              <Suspense fallback={<PageLoader />}>
                <AnalyticsPage />
              </Suspense>
            ),
          },
          {
            path: "/integrations",
            element: (
              <Suspense fallback={<PageLoader />}>
                <IntegrationsPage />
              </Suspense>
            ),
          },
          {
            path: "/social-accounts",
            element: (
              <Suspense fallback={<PageLoader />}>
                <SocialAccountsPage />
              </Suspense>
            ),
          },
          {
            path: "/suggestions",
            element: (
              <Suspense fallback={<PageLoader />}>
                <SuggestionsPage />
              </Suspense>
            ),
          },
          {
            path: "/settings",
            element: (
              <Suspense fallback={<PageLoader />}>
                <SettingsPage />
              </Suspense>
            ),
          },

          // Admin routes
          {
            element: <RequireAdmin />,
            children: [
              {
                path: "/admin",
                element: (
                  <Suspense fallback={<PageLoader />}>
                    <AdminDashboardPage />
                  </Suspense>
                ),
              },
              {
                path: "/admin/users",
                element: (
                  <Suspense fallback={<PageLoader />}>
                    <AdminUsersPage />
                  </Suspense>
                ),
              },
              {
                path: "/admin/settings",
                element: (
                  <Suspense fallback={<PageLoader />}>
                    <AdminSettingsPage />
                  </Suspense>
                ),
              },
            ],
          },
        ],
      },
    ],
  },

  // 404 page
  {
    path: "*",
    element: (
      <Suspense fallback={<PageLoader />}>
        <NotFoundPage />
      </Suspense>
    ),
  },
])

