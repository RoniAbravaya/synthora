/**
 * Video Detail Page
 * 
 * View video details, generation progress, and posting options.
 */

import { useState } from "react"
import { useParams, useNavigate, Link } from "react-router-dom"
import {
  ArrowLeft,
  Video,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  Download,
  Share2,
  Trash2,
  AlertTriangle,
  Copy,
  ExternalLink,
} from "lucide-react"
import { cn, formatRelativeTime, formatDuration } from "@/lib/utils"
import { useVideo, useVideoStatus, useRetryVideo, useDeleteVideo } from "@/hooks/useVideos"
import { videosService } from "@/services/videos"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import type { VideoStatus } from "@/types"
import toast from "react-hot-toast"

// =============================================================================
// Status Configuration
// =============================================================================

const statusSteps = [
  { key: "generating_script", label: "Generating Script", icon: "📝" },
  { key: "generating_voice", label: "Generating Voice", icon: "🎙️" },
  { key: "fetching_media", label: "Fetching Media", icon: "🖼️" },
  { key: "generating_video", label: "Generating Video", icon: "🎬" },
  { key: "assembling", label: "Assembling", icon: "🎞️" },
  { key: "completed", label: "Completed", icon: "✅" },
]

function getStepIndex(status: VideoStatus): number {
  const index = statusSteps.findIndex((s) => s.key === status)
  return index >= 0 ? index : 0
}

function isProcessing(status: VideoStatus): boolean {
  return !["completed", "failed", "pending"].includes(status)
}

// =============================================================================
// Progress Steps Component
// =============================================================================

interface ProgressStepsProps {
  currentStatus: VideoStatus
  progress: number
}

function ProgressSteps({ currentStatus, progress }: ProgressStepsProps) {
  const currentIndex = getStepIndex(currentStatus)
  const isFailed = currentStatus === "failed"

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Generation Progress</span>
        <span className="text-sm text-muted-foreground">{Math.round(progress)}%</span>
      </div>
      <Progress value={progress} className="h-2" />
      
      <div className="grid grid-cols-6 gap-2">
        {statusSteps.map((step, index) => {
          const isActive = index === currentIndex && !isFailed
          const isComplete = index < currentIndex || currentStatus === "completed"
          const isFailedStep = isFailed && index === currentIndex

          return (
            <div
              key={step.key}
              className={cn(
                "flex flex-col items-center gap-1 rounded-lg p-2 text-center transition-colors",
                isActive && "bg-primary/10",
                isComplete && "opacity-60",
                isFailedStep && "bg-destructive/10"
              )}
            >
              <span className="text-xl">
                {isFailedStep ? "❌" : isComplete ? "✓" : step.icon}
              </span>
              <span className="text-[10px] leading-tight text-muted-foreground">
                {step.label}
              </span>
              {isActive && (
                <Loader2 className="h-3 w-3 animate-spin text-primary" />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// =============================================================================
// Error Display Component
// =============================================================================

interface ErrorDisplayProps {
  message: string | null
  payload: Record<string, unknown> | null
  onRetry: () => void
  isRetrying: boolean
}

function ErrorDisplay({ message, payload, onRetry, isRetrying }: ErrorDisplayProps) {
  const [showPayload, setShowPayload] = useState(false)

  return (
    <Card className="border-destructive/50 bg-destructive/5">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-destructive">
          <XCircle className="h-5 w-5" />
          Generation Failed
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm">{message || "An unknown error occurred"}</p>
        
        {payload && (
          <div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowPayload(!showPayload)}
              className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
            >
              {showPayload ? "Hide" : "Show"} Error Details
            </Button>
            {showPayload && (
              <pre className="mt-2 max-h-48 overflow-auto rounded bg-muted p-2 text-xs">
                {JSON.stringify(payload, null, 2)}
              </pre>
            )}
          </div>
        )}

        <div className="flex gap-2">
          <Button onClick={onRetry} disabled={isRetrying}>
            {isRetrying ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            Retry Generation
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

// =============================================================================
// Main Page Component
// =============================================================================

export default function VideoDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)

  const { data: videoData, isLoading } = useVideo(id!)
  const { data: statusData } = useVideoStatus(id!, !!id)
  const retryMutation = useRetryVideo()
  const deleteMutation = useDeleteVideo()

  const video = videoData?.video
  const status = statusData || video

  const handleRetry = async () => {
    if (!id) return
    await retryMutation.mutateAsync(id)
  }

  const handleDelete = async () => {
    if (!id) return
    await deleteMutation.mutateAsync(id)
    navigate("/videos")
  }

  const handleDownload = async () => {
    if (!id || !video?.video_url) return
    try {
      // Create a temporary anchor element to trigger download
      const link = document.createElement("a")
      link.href = video.video_url
      link.download = `${video.title || "video"}.mp4`
      link.target = "_blank"
      link.rel = "noopener noreferrer"
      
      // For cross-origin URLs, we can't force download due to CORS
      // Opening in new tab is the best fallback
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      toast.success("Download started - check your browser's download manager")
    } catch {
      toast.error("Failed to start download")
    }
  }

  const handleCopyLink = async () => {
    if (!video?.video_url) return
    await navigator.clipboard.writeText(video.video_url)
    toast.success("Link copied to clipboard!")
  }

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!video) {
    return (
      <div className="flex h-96 flex-col items-center justify-center">
        <AlertTriangle className="h-12 w-12 text-muted-foreground" />
        <h2 className="mt-4 text-lg font-medium">Video not found</h2>
        <Link to="/videos">
          <Button className="mt-4" variant="outline">
            Back to Videos
          </Button>
        </Link>
      </div>
    )
  }

  const currentStatus = (status?.status || video.status) as VideoStatus
  const progress = status?.progress || video.progress || 0
  const processing = isProcessing(currentStatus)

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold tracking-tight">
            {video.title || "Untitled Video"}
          </h1>
          <p className="text-sm text-muted-foreground">
            Created {formatRelativeTime(video.created_at)}
          </p>
        </div>
        {currentStatus === "completed" && (
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleCopyLink}>
              <Copy className="mr-2 h-4 w-4" />
              Copy Link
            </Button>
            <Button variant="outline" size="sm" onClick={handleDownload}>
              <Download className="mr-2 h-4 w-4" />
              Download
            </Button>
            <Link to={`/posts?video=${video.id}`}>
              <Button size="sm">
                <Share2 className="mr-2 h-4 w-4" />
                Create Post
              </Button>
            </Link>
          </div>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Video Preview */}
        <div className="lg:col-span-2">
          <Card>
            <CardContent className="p-0">
              <div className="relative aspect-video bg-muted">
                {currentStatus === "completed" && video.video_url ? (
                  <video
                    src={video.video_url}
                    controls
                    className="h-full w-full"
                    poster={video.thumbnail_url || undefined}
                  />
                ) : processing ? (
                  <div className="flex h-full flex-col items-center justify-center">
                    <Loader2 className="h-12 w-12 animate-spin text-primary" />
                    <p className="mt-4 text-lg font-medium">
                      {statusSteps.find((s) => s.key === currentStatus)?.label || "Processing..."}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {Math.round(progress)}% complete
                    </p>
                  </div>
                ) : video.thumbnail_url ? (
                  <img
                    src={video.thumbnail_url}
                    alt={video.title || "Video thumbnail"}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center">
                    <Video className="h-16 w-16 text-muted-foreground/50" />
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Progress (when processing) */}
          {(processing || currentStatus === "completed") && (
            <Card className="mt-4">
              <CardContent className="p-4">
                <ProgressSteps currentStatus={currentStatus} progress={progress} />
              </CardContent>
            </Card>
          )}

          {/* Error Display */}
          {currentStatus === "failed" && (
            <div className="mt-4">
              <ErrorDisplay
                message={status?.error_message || video.error_message}
                payload={status?.error_payload || video.error_payload}
                onRetry={handleRetry}
                isRetrying={retryMutation.isPending}
              />
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Status Card */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                {currentStatus === "completed" ? (
                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                ) : currentStatus === "failed" ? (
                  <XCircle className="h-5 w-5 text-destructive" />
                ) : processing ? (
                  <Loader2 className="h-5 w-5 animate-spin text-primary" />
                ) : (
                  <Clock className="h-5 w-5 text-muted-foreground" />
                )}
                <span className="font-medium capitalize">
                  {currentStatus.replace(/_/g, " ")}
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Details Card */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              {video.duration_seconds && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Duration</span>
                  <span>{formatDuration(video.duration_seconds)}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-muted-foreground">Created</span>
                <span>{formatRelativeTime(video.created_at)}</span>
              </div>
              {video.completed_at && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Completed</span>
                  <span>{formatRelativeTime(video.completed_at)}</span>
                </div>
              )}
              {video.expires_at && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Expires</span>
                  <span>{formatRelativeTime(video.expires_at)}</span>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Description Card */}
          {video.description && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Description</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">{video.description}</p>
              </CardContent>
            </Card>
          )}

          {/* Actions Card */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {currentStatus === "failed" && (
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={handleRetry}
                  disabled={retryMutation.isPending}
                >
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Retry Generation
                </Button>
              )}
              {video.video_url && (
                <Button variant="outline" className="w-full" asChild>
                  <a href={video.video_url} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="mr-2 h-4 w-4" />
                    Open in New Tab
                  </a>
                </Button>
              )}
              <Button
                variant="outline"
                className="w-full text-destructive hover:text-destructive"
                onClick={() => setDeleteDialogOpen(true)}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete Video
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Delete Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Video</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this video? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
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
