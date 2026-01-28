/**
 * Videos Page
 * 
 * List of user's generated videos with filtering.
 */

import { useState } from "react"
import { Link } from "react-router-dom"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import {
  Video,
  Plus,
  Loader2,
  Clock,
  CheckCircle2,
  XCircle,
  Play,
  Trash2,
  MoreHorizontal,
  Filter,
  Calendar,
  RefreshCw,
  StopCircle,
  Zap,
  CalendarClock,
  AlertCircle,
} from "lucide-react"
import { cn, formatRelativeTime, formatDate } from "@/lib/utils"
import { useVideos, useDeleteVideo } from "@/hooks/useVideos"
import { videosService } from "@/services/videos"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Progress } from "@/components/ui/progress"
import type { Video as VideoType, VideoStatus } from "@/types"

// =============================================================================
// Status Helpers
// =============================================================================

const statusConfig: Record<string, { label: string; color: string; icon: typeof Clock }> = {
  pending: { label: "Pending", color: "text-muted-foreground", icon: Clock },
  processing: { label: "Processing", color: "text-blue-500", icon: Loader2 },
  generating_script: { label: "Generating Script", color: "text-blue-500", icon: Loader2 },
  generating_voice: { label: "Generating Voice", color: "text-blue-500", icon: Loader2 },
  fetching_media: { label: "Fetching Media", color: "text-blue-500", icon: Loader2 },
  generating_video: { label: "Generating Video", color: "text-blue-500", icon: Loader2 },
  assembling: { label: "Assembling", color: "text-blue-500", icon: Loader2 },
  completed: { label: "Completed", color: "text-green-500", icon: CheckCircle2 },
  failed: { label: "Failed", color: "text-destructive", icon: XCircle },
  cancelled: { label: "Cancelled", color: "text-muted-foreground", icon: StopCircle },
}

const planningStatusConfig: Record<string, { label: string; color: string; icon: typeof Clock }> = {
  planned: { label: "Scheduled", color: "text-amber-500", icon: CalendarClock },
  generating: { label: "Generating", color: "text-blue-500", icon: Loader2 },
  ready: { label: "Ready", color: "text-green-500", icon: CheckCircle2 },
  posting: { label: "Posting", color: "text-blue-500", icon: Loader2 },
  posted: { label: "Posted", color: "text-green-500", icon: CheckCircle2 },
  failed: { label: "Failed", color: "text-destructive", icon: XCircle },
}

function getStatusInfo(status: VideoStatus) {
  return statusConfig[status] || statusConfig.pending
}

function getPlanningStatusInfo(status: string | null | undefined) {
  if (!status || status === "none") return null
  return planningStatusConfig[status] || null
}

function isProcessing(status: VideoStatus) {
  return !["completed", "failed", "pending", "cancelled"].includes(status)
}

function canGenerateNow(video: VideoType) {
  return video.planning_status === "planned"
}

function canCancel(video: VideoType) {
  return ["pending", "processing"].includes(video.status) || 
         video.planning_status === "generating"
}

function canRetry(video: VideoType) {
  return video.status === "failed" || video.planning_status === "failed"
}

// =============================================================================
// Video Card Component
// =============================================================================

interface VideoCardProps {
  video: VideoType
  onDelete: () => void
  onGenerateNow: () => void
  onCancel: () => void
  onRetry: () => void
  isActionPending: boolean
}

function VideoCard({ 
  video, 
  onDelete, 
  onGenerateNow, 
  onCancel, 
  onRetry,
  isActionPending 
}: VideoCardProps) {
  const statusInfo = getStatusInfo(video.status)
  const planningInfo = getPlanningStatusInfo(video.planning_status)
  const StatusIcon = statusInfo.icon
  const processing = isProcessing(video.status)

  // Show planning status if present and not "none"
  const displayPlanningStatus = planningInfo && video.planning_status !== "none"

  return (
    <Card className="group overflow-hidden">
      {/* Thumbnail */}
      <div className="relative aspect-video bg-muted">
        {video.thumbnail_url ? (
          <img
            src={video.thumbnail_url}
            alt={video.title || "Video thumbnail"}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <Video className="h-12 w-12 text-muted-foreground/50" />
          </div>
        )}

        {/* Progress overlay for processing */}
        {processing && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/60">
            <Loader2 className="h-8 w-8 animate-spin text-white" />
            <p className="mt-2 text-sm text-white">{statusInfo.label}</p>
            <Progress value={video.progress} className="mt-2 h-1 w-32" />
          </div>
        )}

        {/* Scheduled badge */}
        {video.scheduled_post_time && video.planning_status === "planned" && (
          <div className="absolute top-2 left-2 flex items-center gap-1 rounded bg-amber-500/90 px-2 py-0.5 text-xs font-medium text-white">
            <CalendarClock className="h-3 w-3" />
            {formatDate(video.scheduled_post_time, "short")}
          </div>
        )}

        {/* Play button for completed */}
        {video.status === "completed" && video.video_url && (
          <Link
            to={`/videos/${video.id}`}
            className="absolute inset-0 flex items-center justify-center bg-black/0 opacity-0 transition-all group-hover:bg-black/40 group-hover:opacity-100"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-white/90">
              <Play className="h-5 w-5 text-black" fill="currentColor" />
            </div>
          </Link>
        )}

        {/* Duration badge */}
        {video.duration_seconds && (
          <div className="absolute bottom-2 right-2 rounded bg-black/70 px-1.5 py-0.5 text-xs text-white">
            {Math.floor(video.duration_seconds / 60)}:{(video.duration_seconds % 60).toString().padStart(2, "0")}
          </div>
        )}
      </div>

      {/* Content */}
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <Link to={`/videos/${video.id}`}>
              <h3 className="truncate font-medium hover:text-primary">
                {video.title || "Untitled Video"}
              </h3>
            </Link>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-sm">
              {displayPlanningStatus ? (
                <>
                  {planningInfo && (
                    <>
                      <planningInfo.icon
                        className={cn(
                          "h-3 w-3",
                          planningInfo.color,
                          video.planning_status === "generating" && "animate-spin"
                        )}
                      />
                      <span className={planningInfo.color}>{planningInfo.label}</span>
                    </>
                  )}
                </>
              ) : (
                <>
                  <StatusIcon
                    className={cn(
                      "h-3 w-3",
                      statusInfo.color,
                      processing && "animate-spin"
                    )}
                  />
                  <span className={statusInfo.color}>{statusInfo.label}</span>
                </>
              )}
              <span className="text-muted-foreground">•</span>
              <span className="text-muted-foreground">
                {formatRelativeTime(video.created_at)}
              </span>
            </div>
            {/* Error message if failed */}
            {video.status === "failed" && video.error_message && (
              <div className="mt-2 flex items-start gap-1 text-xs text-destructive">
                <AlertCircle className="h-3 w-3 mt-0.5 flex-shrink-0" />
                <span className="line-clamp-2">{video.error_message}</span>
              </div>
            )}
          </div>

          {/* Actions */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link to={`/videos/${video.id}`}>View Details</Link>
              </DropdownMenuItem>
              
              {/* Generate Now (for scheduled videos) */}
              {canGenerateNow(video) && (
                <DropdownMenuItem
                  onClick={onGenerateNow}
                  disabled={isActionPending}
                >
                  <Zap className="mr-2 h-4 w-4" />
                  Generate Now
                </DropdownMenuItem>
              )}
              
              {/* Cancel (for processing videos) */}
              {canCancel(video) && (
                <DropdownMenuItem
                  onClick={onCancel}
                  disabled={isActionPending}
                >
                  <StopCircle className="mr-2 h-4 w-4" />
                  Cancel
                </DropdownMenuItem>
              )}
              
              {/* Retry (for failed videos) */}
              {canRetry(video) && (
                <DropdownMenuItem
                  onClick={onRetry}
                  disabled={isActionPending}
                >
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Retry
                </DropdownMenuItem>
              )}
              
              {video.status === "completed" && (
                <DropdownMenuItem asChild>
                  <Link to={`/posts?video=${video.id}`}>Create Post</Link>
                </DropdownMenuItem>
              )}
              
              <DropdownMenuItem
                className="text-destructive"
                onClick={onDelete}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardContent>
    </Card>
  )
}

// =============================================================================
// Main Page Component
// =============================================================================

export default function VideosPage() {
  const [statusFilter, setStatusFilter] = useState<VideoStatus | "all">("all")
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [actionVideoId, setActionVideoId] = useState<string | null>(null)

  const queryClient = useQueryClient()
  const { data, isLoading } = useVideos(
    statusFilter !== "all" ? { status: statusFilter } : undefined
  )
  const deleteMutation = useDeleteVideo()

  // New action mutations
  const generateNowMutation = useMutation({
    mutationFn: (id: string) => videosService.generateNow(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["videos"] })
      setActionVideoId(null)
    },
  })

  const cancelMutation = useMutation({
    mutationFn: (id: string) => videosService.cancel(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["videos"] })
      setActionVideoId(null)
    },
  })

  const retryMutation = useMutation({
    mutationFn: (id: string) => videosService.retry(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["videos"] })
      setActionVideoId(null)
    },
  })

  const videos = data?.videos || []
  const isActionPending = generateNowMutation.isPending || 
                          cancelMutation.isPending || 
                          retryMutation.isPending

  const handleDelete = async () => {
    if (!deleteId) return
    await deleteMutation.mutateAsync(deleteId)
    setDeleteId(null)
  }

  const handleGenerateNow = (videoId: string) => {
    setActionVideoId(videoId)
    generateNowMutation.mutate(videoId)
  }

  const handleCancel = (videoId: string) => {
    setActionVideoId(videoId)
    cancelMutation.mutate(videoId)
  }

  const handleRetry = (videoId: string) => {
    setActionVideoId(videoId)
    retryMutation.mutate(videoId)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">My Videos</h1>
          <p className="text-muted-foreground">
            Manage your generated and scheduled videos
          </p>
        </div>
        <Link to="/create">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Create Video
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Select
            value={statusFilter}
            onValueChange={(value) => setStatusFilter(value as VideoStatus | "all")}
          >
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <span className="text-sm text-muted-foreground">
          {videos.length} video{videos.length !== 1 && "s"}
        </span>
      </div>

      {/* Videos Grid */}
      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : videos.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Video className="h-12 w-12 text-muted-foreground" />
            <h3 className="mt-4 text-lg font-medium">No videos yet</h3>
            <p className="text-sm text-muted-foreground">
              Create your first video to get started.
            </p>
            <Link to="/create">
              <Button className="mt-4">
                <Plus className="mr-2 h-4 w-4" />
                Create Video
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {videos.map((video) => (
            <VideoCard
              key={video.id}
              video={video}
              onDelete={() => setDeleteId(video.id)}
              onGenerateNow={() => handleGenerateNow(video.id)}
              onCancel={() => handleCancel(video.id)}
              onRetry={() => handleRetry(video.id)}
              isActionPending={isActionPending && actionVideoId === video.id}
            />
          ))}
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Video</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this video? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteId(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
