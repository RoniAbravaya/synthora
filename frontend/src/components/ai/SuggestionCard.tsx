/**
 * Suggestion Card
 *
 * Displays a complete AI-generated video suggestion with action buttons.
 */

import { useState } from "react"
import {
  Video,
  Calendar,
  RefreshCw,
  Clock,
  Hash,
  Target,
  Palette,
  MessageSquare,
  ChevronDown,
  ChevronUp,
  TrendingUp,
  BarChart3,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { AISuggestionData } from "@/types"

interface SuggestionCardProps {
  suggestion: AISuggestionData
  dataSource: "analytics" | "trends"
  onGenerateAnother: () => void
  onGenerateVideo: () => void
  onSchedule: () => void
  onRefine: () => void
  isGenerating?: boolean
}

export function SuggestionCard({
  suggestion,
  dataSource,
  onGenerateAnother,
  onGenerateVideo,
  onSchedule,
  onRefine,
  isGenerating = false,
}: SuggestionCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`
  }

  return (
    <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              {dataSource === "analytics" ? (
                <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-green-500/10 text-green-600 dark:text-green-400">
                  <BarChart3 className="h-3 w-3" />
                  Based on your analytics
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400">
                  <TrendingUp className="h-3 w-3" />
                  Based on trends
                </span>
              )}
            </div>
            <CardTitle className="text-xl">{suggestion.title}</CardTitle>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={onGenerateAnother}
            disabled={isGenerating}
          >
            <RefreshCw className={cn("h-4 w-4 mr-2", isGenerating && "animate-spin")} />
            Generate Another
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Description */}
        <p className="text-muted-foreground">{suggestion.description}</p>

        {/* Hook */}
        <div className="rounded-lg bg-muted/50 p-3">
          <p className="text-xs font-medium text-muted-foreground mb-1">Hook (First 3 seconds)</p>
          <p className="text-sm italic">"{suggestion.hook}"</p>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="flex items-center gap-2 text-sm">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <span>{formatDuration(suggestion.estimated_duration_seconds)}</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Target className="h-4 w-4 text-muted-foreground" />
            <span className="truncate">{suggestion.target_audience}</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Palette className="h-4 w-4 text-muted-foreground" />
            <span className="truncate">{suggestion.tone}</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
            <span className="truncate">{suggestion.visual_style.split(",")[0]}</span>
          </div>
        </div>

        {/* Platforms */}
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-2">Recommended Platforms</p>
          <div className="flex flex-wrap gap-2">
            {suggestion.recommended_platforms.map((platform) => (
              <span
                key={platform}
                className="inline-flex items-center rounded-full bg-muted px-3 py-1 text-xs font-medium capitalize"
              >
                {platform}
              </span>
            ))}
          </div>
        </div>

        {/* Hashtags */}
        {suggestion.hashtags.length > 0 && (
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">Suggested Hashtags</p>
            <div className="flex flex-wrap gap-1">
              {suggestion.hashtags.slice(0, 8).map((tag, i) => (
                <span
                  key={i}
                  className="inline-flex items-center text-xs text-primary"
                >
                  <Hash className="h-3 w-3" />
                  {tag}
                </span>
              ))}
              {suggestion.hashtags.length > 8 && (
                <span className="text-xs text-muted-foreground">
                  +{suggestion.hashtags.length - 8} more
                </span>
              )}
            </div>
          </div>
        )}

        {/* Expandable Script Outline */}
        <div className="border-t pt-3">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-2 text-sm font-medium hover:text-primary transition-colors w-full"
          >
            {isExpanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
            Script Outline
          </button>
          {isExpanded && (
            <div className="mt-3 rounded-lg bg-muted/30 p-4">
              <pre className="text-sm whitespace-pre-wrap font-sans">
                {suggestion.script_outline}
              </pre>
            </div>
          )}
        </div>

        {/* Platform-specific notes */}
        {suggestion.platform_specific_notes && isExpanded && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground">Platform Notes</p>
            {Object.entries(suggestion.platform_specific_notes).map(([platform, note]) => (
              <div key={platform} className="text-sm">
                <span className="font-medium capitalize">{platform}:</span>{" "}
                <span className="text-muted-foreground">{note}</span>
              </div>
            ))}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-3 pt-2 border-t">
          <Button onClick={onGenerateVideo} className="gap-2">
            <Video className="h-4 w-4" />
            Generate Video Now
          </Button>
          <Button variant="outline" onClick={onSchedule} className="gap-2">
            <Calendar className="h-4 w-4" />
            Schedule for Later
          </Button>
          <Button variant="ghost" onClick={onRefine} className="gap-2">
            <MessageSquare className="h-4 w-4" />
            Refine This Idea
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
