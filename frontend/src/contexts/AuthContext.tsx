/**
 * Authentication Context
 * 
 * Provides authentication state and methods throughout the app.
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from "react"
import { onAuthChange, signInWithGoogle, signOut, getIdToken, type FirebaseUser } from "@/lib/firebase"
import { apiClient } from "@/lib/api"
import type { User, AuthState } from "@/types"

// =============================================================================
// Types
// =============================================================================

interface AuthContextValue extends AuthState {
  login: () => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

// =============================================================================
// Context
// =============================================================================

const AuthContext = createContext<AuthContextValue | null>(null)

// =============================================================================
// Provider
// =============================================================================

interface AuthProviderProps {
  children: React.ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
  })

  /**
   * Fetch user data from backend after Firebase auth.
   */
  const fetchUser = useCallback(async (firebaseUser: FirebaseUser) => {
    try {
      // Get the Firebase ID token
      const idToken = await firebaseUser.getIdToken()
      
      // Call backend with the ID token for verification
      const response = await apiClient.post<{ user: User; is_new_user: boolean; setup_required: boolean }>("/auth/login", {
        id_token: idToken,
      })
      
      setState({
        user: response.user,
        isLoading: false,
        isAuthenticated: true,
      })
    } catch (error) {
      console.error("Failed to fetch user:", error)
      setState({
        user: null,
        isLoading: false,
        isAuthenticated: false,
      })
    }
  }, [])

  /**
   * Handle Firebase auth state changes.
   */
  useEffect(() => {
    const unsubscribe = onAuthChange(async (firebaseUser) => {
      if (firebaseUser) {
        await fetchUser(firebaseUser)
      } else {
        setState({
          user: null,
          isLoading: false,
          isAuthenticated: false,
        })
      }
    })

    return () => unsubscribe()
  }, [fetchUser])

  /**
   * Sign in with Google.
   */
  const login = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true }))
    try {
      const firebaseUser = await signInWithGoogle()
      await fetchUser(firebaseUser)
    } catch (error) {
      console.error("Login failed:", error)
      setState({
        user: null,
        isLoading: false,
        isAuthenticated: false,
      })
      throw error
    }
  }, [fetchUser])

  /**
   * Sign out.
   */
  const logout = useCallback(async () => {
    try {
      await apiClient.post("/auth/logout")
    } catch (error) {
      console.error("Backend logout failed:", error)
    }
    
    await signOut()
    setState({
      user: null,
      isLoading: false,
      isAuthenticated: false,
    })
  }, [])

  /**
   * Refresh user data from backend.
   */
  const refreshUser = useCallback(async () => {
    try {
      const response = await apiClient.get<{ user: User }>("/auth/me")
      setState((prev) => ({
        ...prev,
        user: response.user,
      }))
    } catch (error) {
      console.error("Failed to refresh user:", error)
    }
  }, [])

  const value: AuthContextValue = {
    ...state,
    login,
    logout,
    refreshUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// =============================================================================
// Hook
// =============================================================================

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}

/**
 * Hook to check if user has a specific role.
 */
export function useHasRole(role: "admin" | "premium" | "free"): boolean {
  const { user } = useAuth()
  if (!user) return false
  
  if (role === "free") return true
  if (role === "premium") return user.role === "premium" || user.role === "admin"
  if (role === "admin") return user.role === "admin"
  
  return false
}

/**
 * Hook to check if user is premium or admin.
 */
export function useIsPremium(): boolean {
  return useHasRole("premium")
}

/**
 * Hook to check if user is admin.
 */
export function useIsAdmin(): boolean {
  return useHasRole("admin")
}

