/**
 * AI Thinking Indicator
 *
 * Animated indicator shown while AI is generating suggestions.
 */

import { Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"

interface AIThinkingIndicatorProps {
  className?: string
  text?: string
}

export function AIThinkingIndicator({
  className,
  text = "AI is thinking...",
}: AIThinkingIndicatorProps) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div className="relative">
        <Sparkles className="h-5 w-5 text-primary animate-pulse" />
        <div className="absolute inset-0 h-5 w-5 bg-primary/20 rounded-full animate-ping" />
      </div>
      <div className="flex items-center gap-1">
        <span className="text-sm text-muted-foreground">{text}</span>
        <span className="flex gap-1">
          <span
            className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce"
            style={{ animationDelay: "0ms" }}
          />
          <span
            className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce"
            style={{ animationDelay: "150ms" }}
          />
          <span
            className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce"
            style={{ animationDelay: "300ms" }}
          />
        </span>
      </div>
    </div>
  )
}
