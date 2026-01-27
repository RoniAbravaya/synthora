/**
 * Posts Page
 * 
 * Manage social media posts with filtering, creation, and actions.
 * Supports creating posts from videos via the ?video= query parameter.
 */

import { useState, useEffect } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  Plus,
  Filter,
  Search,
  MoreHorizontal,
  Calendar,
  Clock,
  Youtube,
  Instagram,
  Facebook,
  Music2,
  Loader2,
  Trash2,
  Eye,
  Send,
  AlertCircle,
  CheckCircle2,
  Video,
  X,
} from "lucide-react"
import { cn, formatDate, formatRelativeTime } from "@/lib/utils"
import { postsService } from "@/services/posts"
import { videosService } from "@/services/videos"
import { useSocialAccounts } from "@/hooks/useSocialAccounts"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
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
  DropdownMenuSeparator,
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
import { Switch } from "@/components/ui/switch"
import toast from "react-hot-toast"
import type { SocialPlatform, Video as VideoType } from "@/types"

// =============================================================================
// Types
// =============================================================================

interface Post {
  id: string
  video_id: string
  platform: string
  caption: string
  hashtags: string[]
  status: "draft" | "scheduled" | "publishing" | "published" | "failed"
  scheduled_at: string | null
  published_at: string | null
  post_url: string | null
  error_message: string | null
  created_at: string
}

// =============================================================================
// Platform Configuration
// =============================================================================

const platformConfig: Record<
  SocialPlatform,
  {
    name: string
    icon: typeof Youtube
    color: string
    bgColor: string
  }
> = {
  youtube: {
    name: "YouTube",
    icon: Youtube,
    color: "text-red-500",
    bgColor: "bg-red-500/10",
  },
  tiktok: {
    name: "TikTok",
    icon: Music2,
    color: "text-foreground",
    bgColor: "bg-foreground/10",
  },
  instagram: {
    name: "Instagram",
    icon: Instagram,
    color: "text-pink-500",
    bgColor: "bg-pink-500/10",
  },
  facebook: {
    name: "Facebook",
    icon: Facebook,
    color: "text-blue-600",
    bgColor: "bg-blue-600/10",
  },
}

const platformIcons: Record<string, React.ReactNode> = {
  youtube: <Youtube className="h-4 w-4 text-red-500" />,
  instagram: <Instagram className="h-4 w-4 text-pink-500" />,
  facebook: <Facebook className="h-4 w-4 text-blue-500" />,
  tiktok: <Music2 className="h-4 w-4" />,
}

const statusColors: Record<string, string> = {
  draft: "bg-gray-500/10 text-gray-500",
  scheduled: "bg-blue-500/10 text-blue-500",
  publishing: "bg-yellow-500/10 text-yellow-500",
  published: "bg-green-500/10 text-green-500",
  failed: "bg-red-500/10 text-red-500",
}

const statusIcons: Record<string, React.ReactNode> = {
  draft: <Clock className="h-3 w-3" />,
  scheduled: <Calendar className="h-3 w-3" />,
  publishing: <Loader2 className="h-3 w-3 animate-spin" />,
  published: <CheckCircle2 className="h-3 w-3" />,
  failed: <AlertCircle className="h-3 w-3" />,
}

// =============================================================================
// Post Card Component
// =============================================================================

interface PostCardProps {
  post: Post
  onDelete: () => void
  onPublish: () => void
}

function PostCard({ post, onDelete, onPublish }: PostCardProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {platformIcons[post.platform]}
            <span className="font-medium capitalize">{post.platform}</span>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {post.post_url && (
                <DropdownMenuItem asChild>
                  <a href={post.post_url} target="_blank" rel="noopener noreferrer">
                    <Eye className="mr-2 h-4 w-4" />
                    View Post
                  </a>
                </DropdownMenuItem>
              )}
              {post.status === "draft" && (
                <DropdownMenuItem onClick={onPublish}>
                  <Send className="mr-2 h-4 w-4" />
                  Publish Now
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={onDelete} className="text-destructive">
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Caption */}
        <p className="line-clamp-2 text-sm">
          {post.caption || "No caption"}
        </p>

        {/* Hashtags */}
        {post.hashtags && post.hashtags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {post.hashtags.slice(0, 3).map((tag) => (
              <span
                key={tag}
                className="rounded bg-primary/10 px-1.5 py-0.5 text-xs text-primary"
              >
                #{tag}
              </span>
            ))}
            {post.hashtags.length > 3 && (
              <span className="text-xs text-muted-foreground">
                +{post.hashtags.length - 3} more
              </span>
            )}
          </div>
        )}

        {/* Status & Time */}
        <div className="flex items-center justify-between">
          <span
            className={cn(
              "flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
              statusColors[post.status]
            )}
          >
            {statusIcons[post.status]}
            {post.status.charAt(0).toUpperCase() + post.status.slice(1)}
          </span>
          <span className="text-xs text-muted-foreground">
            {post.published_at
              ? `Published ${formatRelativeTime(post.published_at)}`
              : post.scheduled_at
              ? `Scheduled for ${formatDate(post.scheduled_at)}`
              : formatRelativeTime(post.created_at)}
          </span>
        </div>

        {/* Error Message */}
        {post.error_message && (
          <div className="rounded bg-destructive/10 p-2 text-xs text-destructive">
            {post.error_message}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// =============================================================================
// Create Post Dialog
// =============================================================================

interface CreatePostDialogProps {
  open: boolean
  onClose: () => void
  videoId: string | null
}

function CreatePostDialog({ open, onClose, videoId }: CreatePostDialogProps) {
  const queryClient = useQueryClient()
  const [selectedPlatforms, setSelectedPlatforms] = useState<SocialPlatform[]>([])
  const [caption, setCaption] = useState("")
  const [hashtags, setHashtags] = useState("")
  const [publishNow, setPublishNow] = useState(true)

  // Fetch the video details
  const { data: videoData, isLoading: videoLoading } = useQuery({
    queryKey: ["video", videoId],
    queryFn: () => videosService.get(videoId!),
    enabled: !!videoId && open,
  })

  // Fetch connected social accounts
  const { data: accountsData, isLoading: accountsLoading } = useSocialAccounts()

  const video = videoData?.video
  const connectedAccounts = accountsData?.accounts || []
  const connectedPlatforms = [...new Set(connectedAccounts.map((a) => a.platform as SocialPlatform))]

  // Create post mutation
  const createMutation = useMutation({
    mutationFn: async () => {
      if (!videoId || selectedPlatforms.length === 0) {
        throw new Error("Please select at least one platform")
      }

      const hashtagList = hashtags
        .split(/[\s,#]+/)
        .map((t) => t.trim())
        .filter((t) => t.length > 0)

      const response = await postsService.create({
        video_id: videoId,
        title: video?.title || "New Video",
        description: caption,
        platforms: selectedPlatforms,
        scheduled_at: publishNow ? undefined : undefined, // For now, always publish now or draft
      })

      // If publish now is selected, publish immediately
      if (publishNow && response.post) {
        await postsService.publishNow(response.post.id)
      }

      return response
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["posts"] })
      toast.success(publishNow ? "Post published!" : "Post created as draft")
      handleClose()
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to create post")
    },
  })

  const handleClose = () => {
    setSelectedPlatforms([])
    setCaption("")
    setHashtags("")
    setPublishNow(true)
    onClose()
  }

  const togglePlatform = (platform: SocialPlatform) => {
    setSelectedPlatforms((prev) =>
      prev.includes(platform)
        ? prev.filter((p) => p !== platform)
        : [...prev, platform]
    )
  }

  const isLoading = videoLoading || accountsLoading

  return (
    <Dialog open={open} onOpenChange={(o) => !o && handleClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Create Post</DialogTitle>
          <DialogDescription>
            Share your video to connected social media accounts
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : !video ? (
          <div className="flex flex-col items-center justify-center py-8">
            <AlertCircle className="h-8 w-8 text-muted-foreground" />
            <p className="mt-2 text-sm text-muted-foreground">Video not found</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Video Preview */}
            <div className="flex gap-4">
              <div className="h-20 w-32 flex-shrink-0 overflow-hidden rounded-lg bg-muted">
                {video.thumbnail_url ? (
                  <img
                    src={video.thumbnail_url}
                    alt={video.title || "Video"}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center">
                    <Video className="h-8 w-8 text-muted-foreground" />
                  </div>
                )}
              </div>
              <div className="flex-1">
                <h4 className="font-medium">{video.title || "Untitled Video"}</h4>
                <p className="text-sm text-muted-foreground">
                  Created {formatRelativeTime(video.created_at)}
                </p>
              </div>
            </div>

            {/* Platform Selection */}
            <div className="space-y-3">
              <Label>Select Platforms</Label>
              {connectedPlatforms.length === 0 ? (
                <Card className="border-dashed">
                  <CardContent className="flex flex-col items-center justify-center py-6">
                    <AlertCircle className="h-8 w-8 text-muted-foreground" />
                    <p className="mt-2 text-sm text-muted-foreground">
                      No social accounts connected
                    </p>
                    <Link to="/social-accounts">
                      <Button variant="outline" size="sm" className="mt-4">
                        Connect Accounts
                      </Button>
                    </Link>
                  </CardContent>
                </Card>
              ) : (
                <div className="grid grid-cols-2 gap-2">
                  {connectedPlatforms.map((platform) => {
                    const config = platformConfig[platform]
                    const Icon = config.icon
                    const isSelected = selectedPlatforms.includes(platform)

                    return (
                      <button
                        key={platform}
                        onClick={() => togglePlatform(platform)}
                        className={cn(
                          "flex items-center gap-3 rounded-lg border p-3 text-left transition-colors",
                          isSelected
                            ? "border-primary bg-primary/5"
                            : "border-border hover:bg-muted/50"
                        )}
                      >
                        <div
                          className={cn(
                            "flex h-8 w-8 items-center justify-center rounded-lg",
                            config.bgColor
                          )}
                        >
                          <Icon className={cn("h-4 w-4", config.color)} />
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-medium">{config.name}</p>
                        </div>
                        {isSelected && (
                          <CheckCircle2 className="h-4 w-4 text-primary" />
                        )}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Caption */}
            <div className="space-y-2">
              <Label htmlFor="caption">Caption</Label>
              <Textarea
                id="caption"
                placeholder="Write a caption for your post..."
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
                rows={3}
              />
            </div>

            {/* Hashtags */}
            <div className="space-y-2">
              <Label htmlFor="hashtags">Hashtags</Label>
              <Input
                id="hashtags"
                placeholder="#viral #trending #content"
                value={hashtags}
                onChange={(e) => setHashtags(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Separate hashtags with spaces or commas
              </p>
            </div>

            {/* Publish Option */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Publish Immediately</Label>
                <p className="text-xs text-muted-foreground">
                  {publishNow ? "Post will be published now" : "Post will be saved as draft"}
                </p>
              </div>
              <Switch checked={publishNow} onCheckedChange={setPublishNow} />
            </div>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            onClick={() => createMutation.mutate()}
            disabled={
              createMutation.isPending ||
              selectedPlatforms.length === 0 ||
              !video
            }
          >
            {createMutation.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            {publishNow ? "Publish" : "Save as Draft"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// =============================================================================
// Main Page Component
// =============================================================================

export default function PostsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [platformFilter, setPlatformFilter] = useState<string>("all")
  const [deleteId, setDeleteId] = useState<string | null>(null)

  // Get video ID from URL params
  const videoIdFromUrl = searchParams.get("video")
  const [createDialogOpen, setCreateDialogOpen] = useState(!!videoIdFromUrl)
  const [selectedVideoId, setSelectedVideoId] = useState<string | null>(videoIdFromUrl)

  // Open create dialog when video param is present
  useEffect(() => {
    if (videoIdFromUrl) {
      setSelectedVideoId(videoIdFromUrl)
      setCreateDialogOpen(true)
    }
  }, [videoIdFromUrl])

  const handleCloseCreateDialog = () => {
    setCreateDialogOpen(false)
    setSelectedVideoId(null)
    // Remove video param from URL
    if (videoIdFromUrl) {
      searchParams.delete("video")
      setSearchParams(searchParams)
    }
  }

  const queryClient = useQueryClient()

  // Fetch posts
  const { data, isLoading } = useQuery({
    queryKey: ["posts", statusFilter, platformFilter],
    queryFn: () =>
      postsService.list({
        status: statusFilter !== "all" ? statusFilter : undefined,
        platform: platformFilter !== "all" ? platformFilter : undefined,
      }),
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: postsService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["posts"] })
      toast.success("Post deleted")
      setDeleteId(null)
    },
    onError: () => {
      toast.error("Failed to delete post")
    },
  })

  // Publish mutation
  const publishMutation = useMutation({
    mutationFn: postsService.publishNow,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["posts"] })
      toast.success("Post published!")
    },
    onError: () => {
      toast.error("Failed to publish post")
    },
  })

  const posts: Post[] = data?.posts || []

  // Filter by search
  const filteredPosts = posts.filter(
    (post) =>
      post.caption?.toLowerCase().includes(search.toLowerCase()) ||
      post.hashtags?.some((tag) => tag.toLowerCase().includes(search.toLowerCase()))
  )

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Posts</h1>
          <p className="text-muted-foreground">
            Manage your social media posts
          </p>
        </div>
        <div className="flex gap-2">
          <Link to="/calendar">
            <Button variant="outline">
              <Calendar className="mr-2 h-4 w-4" />
              Calendar
            </Button>
          </Link>
          <Link to="/videos">
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Create Video
            </Button>
          </Link>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search posts..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex gap-2">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-36">
              <Filter className="mr-2 h-4 w-4" />
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="draft">Draft</SelectItem>
              <SelectItem value="scheduled">Scheduled</SelectItem>
              <SelectItem value="published">Published</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
            </SelectContent>
          </Select>
          <Select value={platformFilter} onValueChange={setPlatformFilter}>
            <SelectTrigger className="w-36">
              <SelectValue placeholder="Platform" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Platforms</SelectItem>
              <SelectItem value="youtube">YouTube</SelectItem>
              <SelectItem value="instagram">Instagram</SelectItem>
              <SelectItem value="tiktok">TikTok</SelectItem>
              <SelectItem value="facebook">Facebook</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Posts Grid */}
      {filteredPosts.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Calendar className="h-12 w-12 text-muted-foreground" />
            <h3 className="mt-4 text-lg font-medium">No posts yet</h3>
            <p className="text-sm text-muted-foreground">
              Generate a video and schedule it for posting.
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
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredPosts.map((post) => (
            <PostCard
              key={post.id}
              post={post}
              onDelete={() => setDeleteId(post.id)}
              onPublish={() => publishMutation.mutate(post.id)}
            />
          ))}
        </div>
      )}

      {/* Delete Confirmation */}
      <Dialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Post</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this post? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteId(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteId && deleteMutation.mutate(deleteId)}
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

      {/* Create Post Dialog */}
      <CreatePostDialog
        open={createDialogOpen}
        onClose={handleCloseCreateDialog}
        videoId={selectedVideoId}
      />
    </div>
  )
}
