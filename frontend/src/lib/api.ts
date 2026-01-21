/**
 * API Client
 * 
 * Axios instance configured for the backend API with authentication.
 */

import axios, { type AxiosError, type AxiosRequestConfig } from "axios"
import { getIdToken } from "./firebase"

// Base URL for API requests
const API_BASE_URL = import.meta.env.VITE_API_URL || "/api/v1"

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  async (config) => {
    const token = await getIdToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string; message?: string }>) => {
    // Handle specific error codes
    if (error.response?.status === 401) {
      // Unauthorized - redirect to login
      window.location.href = "/login"
    }
    
    // Extract error message
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      "An unexpected error occurred"
    
    // Create a more informative error
    const enhancedError = new Error(message) as Error & {
      status?: number
      originalError?: AxiosError
    }
    enhancedError.status = error.response?.status
    enhancedError.originalError = error
    
    return Promise.reject(enhancedError)
  }
)

// Type-safe API methods
export const apiClient = {
  get: <T>(url: string, config?: AxiosRequestConfig) =>
    api.get<T>(url, config).then((res) => res.data),
  
  post: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    api.post<T>(url, data, config).then((res) => res.data),
  
  put: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    api.put<T>(url, data, config).then((res) => res.data),
  
  patch: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    api.patch<T>(url, data, config).then((res) => res.data),
  
  delete: <T>(url: string, config?: AxiosRequestConfig) =>
    api.delete<T>(url, config).then((res) => res.data),
}

export default api

