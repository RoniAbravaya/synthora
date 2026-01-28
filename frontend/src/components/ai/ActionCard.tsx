/**
 * Action Card
 *
 * Actionable card within chat responses for executing
 * video creation, scheduling, and planning actions.
 */

import {
  Video,
  Calendar,
  List,
  CalendarDays,
  Play,
  ChevronRight,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import type { ActionCard as ActionCardType } from "@/types"

interface ActionCardProps {
  card: ActionCardType
  onExecute: () => void
}

const typeIcons = {
  single_video: Video,
  series: List,
  monthly_plan: CalendarDays,
  schedule: Calendar,
}

const typeLabels = {
  single_video: "Create Video",
  series: "Create Series",
  monthly_plan: "Create Plan",
  schedule: "Schedule",
}

const typeColors = {
  single_video: "bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20",
  series: "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20",
  monthly_plan: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20",
  schedule: "bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20",
}

export function ActionCard({ card, onExecute }: ActionCardProps) {
  const Icon = typeIcons[card.type] || Video
  const label = typeLabels[card.type] || "Execute"
  const colorClass = typeColors[card.type] || typeColors.single_video

  // Extract relevant info from card data for preview
  const previewInfo = getPreviewInfo(card)

  return (
    <Card className={`border ${colorClass} bg-transparent`}>
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-lg ${colorClass}`}>
            <Icon className="h-4 w-4" />
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="font-medium text-sm">{card.title}</h4>
            {card.description && (
              <p className="text-xs text-muted-foreground mt-1">{card.description}</p>
            )}
            
            {/* Preview Info */}
            {previewInfo && (
              <div className="mt-2 space-y-1">
                {previewInfo.map((info, index) => (
                  <p key={index} className="text-xs text-muted-foreground">
                    {info}
                  </p>
                ))}
              </div>
            )}
          </div>
          <Button size="sm" onClick={onExecute} className="shrink-0 gap-1">
            <Play className="h-3 w-3" />
            {label}
            <ChevronRight className="h-3 w-3" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function getPreviewInfo(card: ActionCardType): string[] | null {
  const data = card.data
  const info: string[] = []

  if (card.type === "single_video") {
    const suggestion = data.suggestion as Record<string, unknown> | undefined
    if (suggestion?.estimated_duration_seconds) {
      info.push(`Duration: ~${suggestion.estimated_duration_seconds}s`)
    }
    if (suggestion?.recommended_platforms) {
      const platforms = suggestion.recommended_platforms as string[]
      info.push(`Platforms: ${platforms.slice(0, 3).join(", ")}`)
    }
  }

  if (card.type === "series") {
    const videos = data.videos as unknown[] | undefined
    if (videos?.length) {
      info.push(`${videos.length} videos in the series`)
    }
    const schedule = data.schedule as unknown[] | undefined
    if (schedule?.length) {
      info.push(`Scheduled over ${schedule.length} days`)
    }
  }

  if (card.type === "monthly_plan") {
    const plan = data.plan as Record<string, unknown> | undefined
    if (plan?.total_videos) {
      info.push(`${plan.total_videos} videos planned`)
    }
    if (plan?.month) {
      info.push(`For ${plan.month}`)
    }
  }

  if (card.type === "schedule") {
    const time = data.proposed_time as string | undefined
    if (time) {
      try {
        const date = new Date(time)
        info.push(`Scheduled for ${date.toLocaleDateString()} at ${date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`)
      } catch {
        // Ignore date parsing errors
      }
    }
    const platforms = data.target_platforms as string[] | undefined
    if (platforms?.length) {
      info.push(`Post to: ${platforms.join(", ")}`)
    }
  }

  return info.length > 0 ? info : null
}
