/**
 * Utility functions for the frontend application.
 */

import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * Combines class names using clsx and tailwind-merge.
 * This ensures Tailwind classes are properly merged without conflicts.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Formats a date to a human-readable string.
 * Returns "N/A" if the date is null or undefined.
 */
export function formatDate(date: Date | string | null | undefined): string {
  if (date === null || date === undefined) {
    return "N/A"
  }
  const d = typeof date === "string" ? new Date(date) : date
  // Check for invalid date
  if (isNaN(d.getTime())) {
    return "N/A"
  }
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  })
}

/**
 * Formats a date to a relative time string (e.g., "2 hours ago").
 * Returns "N/A" if the date is null or undefined.
 */
export function formatRelativeTime(date: Date | string | null | undefined): string {
  if (date === null || date === undefined) {
    return "N/A"
  }
  const d = typeof date === "string" ? new Date(date) : date
  // Check for invalid date
  if (isNaN(d.getTime())) {
    return "N/A"
  }
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  
  if (days > 7) {
    return formatDate(d)
  } else if (days > 0) {
    return `${days}d ago`
  } else if (hours > 0) {
    return `${hours}h ago`
  } else if (minutes > 0) {
    return `${minutes}m ago`
  } else {
    return "Just now"
  }
}

/**
 * Truncates a string to a maximum length with ellipsis.
 */
export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str
  return str.slice(0, maxLength - 3) + "..."
}

/**
 * Capitalizes the first letter of a string.
 */
export function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1)
}

/**
 * Formats a number with commas as thousands separators.
 */
export function formatNumber(num: number | null | undefined): string {
  if (num === null || num === undefined) return "0"
  return num.toLocaleString("en-US")
}

/**
 * Formats a number in a compact format (e.g., 1.2K, 3.4M).
 */
export function formatCompactNumber(num: number | null | undefined): string {
  if (num === null || num === undefined) return "0"
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + "M"
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + "K"
  }
  return num.toString()
}

/**
 * Formats currency in USD.
 */
export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(amount)
}

/**
 * Formats a duration in seconds to a human-readable string.
 */
export function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, "0")}`
}

/**
 * Generates a random ID.
 */
export function generateId(): string {
  return Math.random().toString(36).substring(2, 15)
}

/**
 * Debounces a function call.
 */
export function debounce<T extends (...args: unknown[]) => void>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null
  
  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null
      func(...args)
    }
    
    if (timeout) {
      clearTimeout(timeout)
    }
    timeout = setTimeout(later, wait)
  }
}

/**
 * Copies text to clipboard.
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}

/**
 * Gets platform icon name for social media.
 */
export function getPlatformIcon(platform: string): string {
  const icons: Record<string, string> = {
    youtube: "Youtube",
    tiktok: "Music2",
    instagram: "Instagram",
    facebook: "Facebook",
  }
  return icons[platform.toLowerCase()] || "Globe"
}

/**
 * Gets platform color for social media.
 */
export function getPlatformColor(platform: string): string {
  const colors: Record<string, string> = {
    youtube: "#FF0000",
    tiktok: "#000000",
    instagram: "#E4405F",
    facebook: "#1877F2",
  }
  return colors[platform.toLowerCase()] || "#6B7280"
}

