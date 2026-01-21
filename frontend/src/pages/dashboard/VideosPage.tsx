/**
 * Videos Page
 * 
 * List of user's generated videos with filtering.
 */

import { useState } from "react"
import { Link } from "react-router-dom"
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
} from "lucide-react"
import { cn, formatRelativeTime } from "@/lib/utils"
import { useVideos, useDeleteVideo } from "@/hooks/useVideos"
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

const statusConfig: Record<VideoStatus, { label: string; color: string; icon: typeof Clock }> = {
  pending: { label: "Pending", color: "text-muted-foreground", icon: Clock },
  generating_script: { label: "Generating Script", color: "text-blue-500", icon: Loader2 },
  generating_voice: { label: "Generating Voice", color: "text-blue-500", icon: Loader2 },
  fetching_media: { label: "Fetching Media", color: "text-blue-500", icon: Loader2 },
  generating_video: { label: "Generating Video", color: "text-blue-500", icon: Loader2 },
  assembling: { label: "Assembling", color: "text-blue-500", icon: Loader2 },
  completed: { label: "Completed", color: "text-green-500", icon: CheckCircle2 },
  failed: { label: "Failed", color: "text-destructive", icon: XCircle },
}

function getStatusInfo(status: VideoStatus) {
  return statusConfig[status] || statusConfig.pending
}

function isProcessing(status: VideoStatus) {
  return !["completed", "failed", "pending"].includes(status)
}

// =============================================================================
// Video Card Component
// =============================================================================

interface VideoCardProps {
  video: VideoType
  onDelete: () => void
}

function VideoCard({ video, onDelete }: VideoCardProps) {
  const statusInfo = getStatusInfo(video.status)
  const StatusIcon = statusInfo.icon
  const processing = isProcessing(video.status)

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
            <div className="mt-1 flex items-center gap-2 text-sm">
              <StatusIcon
                className={cn(
                  "h-3 w-3",
                  statusInfo.color,
                  processing && "animate-spin"
                )}
              />
              <span className={statusInfo.color}>{statusInfo.label}</span>
              <span className="text-muted-foreground">•</span>
              <span className="text-muted-foreground">
                {formatRelativeTime(video.created_at)}
              </span>
            </div>
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

  const { data, isLoading } = useVideos(
    statusFilter !== "all" ? { status: statusFilter } : undefined
  )
  const deleteMutation = useDeleteVideo()

  const videos = data?.videos || []

  const handleDelete = async () => {
    if (!deleteId) return
    await deleteMutation.mutateAsync(deleteId)
    setDeleteId(null)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">My Videos</h1>
          <p className="text-muted-foreground">
            Manage your generated videos
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
