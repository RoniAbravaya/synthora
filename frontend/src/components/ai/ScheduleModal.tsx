/**
 * Schedule Modal
 *
 * Modal for scheduling a video for future generation and posting.
 */

import { useState } from "react"
import { Calendar, Clock, Globe } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import type { AISuggestionData } from "@/types"

interface ScheduleModalProps {
  open: boolean
  onClose: () => void
  onSchedule: (scheduledTime: string, platforms: string[]) => void
  suggestion: AISuggestionData
  isLoading?: boolean
}

const PLATFORMS = [
  { id: "youtube", label: "YouTube" },
  { id: "tiktok", label: "TikTok" },
  { id: "instagram", label: "Instagram" },
  { id: "facebook", label: "Facebook" },
]

export function ScheduleModal({
  open,
  onClose,
  onSchedule,
  suggestion,
  isLoading = false,
}: ScheduleModalProps) {
  // Default to 2 hours from now
  const defaultDate = new Date(Date.now() + 2 * 60 * 60 * 1000)
  const [date, setDate] = useState(defaultDate.toISOString().split("T")[0])
  const [time, setTime] = useState(
    defaultDate.toTimeString().slice(0, 5)
  )
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(
    suggestion.recommended_platforms || ["youtube", "tiktok"]
  )

  const togglePlatform = (platformId: string) => {
    setSelectedPlatforms((prev) =>
      prev.includes(platformId)
        ? prev.filter((p) => p !== platformId)
        : [...prev, platformId]
    )
  }

  const handleSchedule = () => {
    if (selectedPlatforms.length === 0) return
    const scheduledTime = new Date(`${date}T${time}`).toISOString()
    onSchedule(scheduledTime, selectedPlatforms)
  }

  const minDate = new Date(Date.now() + 2 * 60 * 60 * 1000)
    .toISOString()
    .split("T")[0]

  return (
    <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Schedule Video</DialogTitle>
          <DialogDescription>
            Choose when to generate and post "{suggestion.title}"
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Date & Time */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="date" className="flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                Date
              </Label>
              <Input
                id="date"
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                min={minDate}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="time" className="flex items-center gap-2">
                <Clock className="h-4 w-4" />
                Time
              </Label>
              <Input
                id="time"
                type="time"
                value={time}
                onChange={(e) => setTime(e.target.value)}
              />
            </div>
          </div>

          {/* Platform Selection */}
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              <Globe className="h-4 w-4" />
              Platforms
            </Label>
            <div className="flex flex-wrap gap-2">
              {PLATFORMS.map((platform) => (
                <Button
                  key={platform.id}
                  type="button"
                  variant={selectedPlatforms.includes(platform.id) ? "default" : "outline"}
                  size="sm"
                  onClick={() => togglePlatform(platform.id)}
                >
                  {platform.label}
                </Button>
              ))}
            </div>
            {selectedPlatforms.length === 0 && (
              <p className="text-xs text-destructive">
                Please select at least one platform
              </p>
            )}
          </div>

          {/* Info */}
          <div className="rounded-lg bg-muted/50 p-3 text-sm">
            <p className="text-muted-foreground">
              Video will be generated 1 hour before the scheduled time and
              automatically posted to the selected platforms.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            onClick={handleSchedule}
            disabled={isLoading || selectedPlatforms.length === 0}
          >
            {isLoading ? "Scheduling..." : "Schedule Video"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
