/**
 * Posts Page
 * 
 * Manage social media posts with filtering and actions.
 */

import { useState } from "react"
import { Link } from "react-router-dom"
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
} from "lucide-react"
import { cn, formatDate, formatRelativeTime } from "@/lib/utils"
import { postsService } from "@/services/posts"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
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
import toast from "react-hot-toast"

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
// Platform Icons
// =============================================================================

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
// Main Page Component
// =============================================================================

export default function PostsPage() {
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [platformFilter, setPlatformFilter] = useState<string>("all")
  const [deleteId, setDeleteId] = useState<string | null>(null)

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
    </div>
  )
}
