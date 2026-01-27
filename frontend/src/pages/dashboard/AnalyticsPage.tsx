/**
 * Analytics Page
 * 
 * View performance analytics across all platforms.
 */

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import {
  BarChart3,
  TrendingUp,
  Eye,
  Heart,
  MessageCircle,
  Share2,
  Youtube,
  Instagram,
  Facebook,
  Music2,
  Loader2,
  Calendar,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  Play,
  ExternalLink,
} from "lucide-react"
import { cn, formatNumber, formatCompactNumber, formatRelativeTime } from "@/lib/utils"
import { analyticsService } from "@/services/analytics"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"

// =============================================================================
// Types
// =============================================================================

interface AnalyticsOverview {
  total_views: number
  total_likes: number
  total_comments: number
  total_shares: number
  total_posts: number
  avg_engagement_rate: number
  views_change: number
  likes_change: number
  comments_change: number
  shares_change: number
}

interface PlatformStats {
  platform: string
  views: number
  likes: number
  comments: number
  shares: number
  posts: number
  engagement_rate: number
}

// =============================================================================
// Platform Icons
// =============================================================================

const platformIcons: Record<string, React.ReactNode> = {
  youtube: <Youtube className="h-5 w-5 text-red-500" />,
  instagram: <Instagram className="h-5 w-5 text-pink-500" />,
  facebook: <Facebook className="h-5 w-5 text-blue-500" />,
  tiktok: <Music2 className="h-5 w-5" />,
}

const platformColors: Record<string, string> = {
  youtube: "bg-red-500",
  instagram: "bg-gradient-to-r from-purple-500 to-pink-500",
  facebook: "bg-blue-500",
  tiktok: "bg-gray-800",
}

// =============================================================================
// Stat Card Component
// =============================================================================

interface StatCardProps {
  title: string
  value: number
  change?: number | null
  icon: React.ReactNode
  format?: "number" | "compact" | "percent"
}

function StatCard({ title, value, change, icon, format = "compact" }: StatCardProps) {
  const safeValue = value ?? 0
  const safeChange = change ?? 0
  const hasChange = change !== null && change !== undefined
  const isPositive = safeChange >= 0
  const formattedValue =
    format === "percent"
      ? `${safeValue.toFixed(1)}%`
      : format === "compact"
      ? formatCompactNumber(safeValue)
      : formatNumber(safeValue)

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        {icon}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{formattedValue}</div>
        {hasChange && (
          <div
            className={cn(
              "mt-1 flex items-center text-xs",
              isPositive ? "text-green-500" : "text-red-500"
            )}
          >
            {isPositive ? (
              <ArrowUpRight className="mr-1 h-3 w-3" />
            ) : (
              <ArrowDownRight className="mr-1 h-3 w-3" />
            )}
            {Math.abs(safeChange).toFixed(1)}% from last period
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// =============================================================================
// Platform Card Component
// =============================================================================

interface PlatformCardProps {
  stats: PlatformStats
}

function PlatformCard({ stats }: PlatformCardProps) {
  const engagementRate = stats.engagement_rate ?? 0
  const posts = stats.posts ?? 0
  
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-lg",
              stats.platform === "instagram" 
                ? "bg-gradient-to-r from-purple-500/10 to-pink-500/10" 
                : `${platformColors[stats.platform]?.replace("bg-", "bg-")}/10`
            )}
          >
            {platformIcons[stats.platform] || <BarChart3 className="h-5 w-5" />}
          </div>
          <div>
            <CardTitle className="text-base capitalize">{stats.platform}</CardTitle>
            <CardDescription>{posts} posts</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-muted-foreground">Views</p>
            <p className="text-lg font-semibold">{formatCompactNumber(stats.views)}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Likes</p>
            <p className="text-lg font-semibold">{formatCompactNumber(stats.likes)}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Comments</p>
            <p className="text-lg font-semibold">{formatCompactNumber(stats.comments)}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Shares</p>
            <p className="text-lg font-semibold">{formatCompactNumber(stats.shares)}</p>
          </div>
        </div>

        <div>
          <div className="mb-1 flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Engagement Rate</span>
            <span className="font-medium">{engagementRate.toFixed(1)}%</span>
          </div>
          <Progress value={Math.min(engagementRate * 10, 100)} className="h-2" />
        </div>
      </CardContent>
    </Card>
  )
}

// =============================================================================
// Time Series Chart (Simple Bar Chart)
// =============================================================================

interface TimeSeriesChartProps {
  data: Array<{ date: string; value: number }>
  metric: string
  color?: string
}

function TimeSeriesChart({ data, metric, color = "bg-primary" }: TimeSeriesChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">
        No data available
      </div>
    )
  }

  const maxValue = Math.max(...data.map(d => d.value), 1)
  const total = data.reduce((sum, d) => sum + d.value, 0)

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium capitalize">{metric}</span>
        <span className="text-muted-foreground">
          Total: {formatCompactNumber(total)}
        </span>
      </div>
      <div className="flex h-32 items-end gap-1">
        {data.map((d, i) => (
          <div
            key={i}
            className="group relative flex-1"
          >
            <div
              className={cn("w-full rounded-t transition-all hover:opacity-80", color)}
              style={{ height: `${Math.max((d.value / maxValue) * 100, 2)}%` }}
            />
            <div className="absolute -top-8 left-1/2 -translate-x-1/2 rounded bg-popover px-2 py-1 text-xs opacity-0 shadow-md transition-opacity group-hover:opacity-100 whitespace-nowrap z-10">
              {d.date}: {formatCompactNumber(d.value)}
            </div>
          </div>
        ))}
      </div>
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{data[0]?.date}</span>
        <span>{data[data.length - 1]?.date}</span>
      </div>
    </div>
  )
}

// =============================================================================
// Top Performing Item
// =============================================================================

interface TopPerformingItemProps {
  item: {
    post_id: string
    video_id: string
    title: string
    thumbnail_url: string | null
    platforms: string[]
    published_at: string | null
    metrics: {
      views: number
      likes: number
      comments: number
      shares: number
    }
  }
  rank: number
}

function TopPerformingItemCard({ item, rank }: TopPerformingItemProps) {
  return (
    <div className="flex items-center gap-4 rounded-lg border p-3 hover:bg-muted/50 transition-colors">
      <span className="text-2xl font-bold text-muted-foreground w-8 text-center">
        {rank}
      </span>
      <div className="h-16 w-28 rounded bg-muted flex items-center justify-center overflow-hidden shrink-0">
        {item.thumbnail_url ? (
          <img 
            src={item.thumbnail_url} 
            alt={item.title} 
            className="h-full w-full object-cover"
          />
        ) : (
          <Play className="h-6 w-6 text-muted-foreground" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <Link 
          to={`/videos/${item.video_id}`}
          className="font-medium hover:underline line-clamp-1"
        >
          {item.title || "Untitled"}
        </Link>
        <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
          {item.platforms?.map((p) => (
            <span key={p} className="capitalize">{p}</span>
          ))}
          {item.published_at && (
            <>
              <span>•</span>
              <span>{formatRelativeTime(item.published_at)}</span>
            </>
          )}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-right">
        <div className="flex items-center justify-end gap-1 text-sm">
          <Eye className="h-3 w-3 text-muted-foreground" />
          {formatCompactNumber(item.metrics?.views || 0)}
        </div>
        <div className="flex items-center justify-end gap-1 text-sm">
          <Heart className="h-3 w-3 text-muted-foreground" />
          {formatCompactNumber(item.metrics?.likes || 0)}
        </div>
        <div className="flex items-center justify-end gap-1 text-sm">
          <MessageCircle className="h-3 w-3 text-muted-foreground" />
          {formatCompactNumber(item.metrics?.comments || 0)}
        </div>
        <div className="flex items-center justify-end gap-1 text-sm">
          <Share2 className="h-3 w-3 text-muted-foreground" />
          {formatCompactNumber(item.metrics?.shares || 0)}
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Helper Functions
// =============================================================================

function periodToDays(period: string): number {
  switch (period) {
    case "7d": return 7
    case "30d": return 30
    case "90d": return 90
    case "1y": return 365
    default: return 30
  }
}

// =============================================================================
// Main Page Component
// =============================================================================

export default function AnalyticsPage() {
  const [period, setPeriod] = useState("30d")
  const [timeSeriesMetric, setTimeSeriesMetric] = useState("views")
  const queryClient = useQueryClient()

  const days = periodToDays(period)

  // Fetch analytics overview
  const { data: overviewData, isLoading: overviewLoading } = useQuery({
    queryKey: ["analytics", "overview", days],
    queryFn: () => analyticsService.getOverview(days),
  })

  // Fetch platform comparison
  const { data: platformData, isLoading: platformLoading } = useQuery({
    queryKey: ["analytics", "platforms", days],
    queryFn: () => analyticsService.getPlatformComparison(days),
  })

  // Fetch time series data
  const { data: timeSeriesData, isLoading: timeSeriesLoading } = useQuery({
    queryKey: ["analytics", "timeSeries", timeSeriesMetric, days],
    queryFn: () => analyticsService.getTimeSeries(timeSeriesMetric, period as "7d" | "30d" | "90d"),
  })

  // Fetch top performing
  const { data: topPerformingData, isLoading: topPerformingLoading } = useQuery({
    queryKey: ["analytics", "topPerforming", "views", 5],
    queryFn: () => analyticsService.getTopPerforming("views", 5),
  })

  // Sync mutation
  const syncMutation = useMutation({
    mutationFn: () => analyticsService.sync(),
    onSuccess: () => {
      // Invalidate all analytics queries after a delay
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["analytics"] })
      }, 3000)
    },
  })

  // Map API response to expected structure with safe defaults
  const overview: AnalyticsOverview = {
    total_views: overviewData?.summary?.views ?? 0,
    total_likes: overviewData?.summary?.likes ?? 0,
    total_comments: overviewData?.summary?.comments ?? 0,
    total_shares: overviewData?.summary?.shares ?? 0,
    total_posts: overviewData?.total_posts ?? 0,
    avg_engagement_rate: overviewData?.summary?.engagement_rate ?? 0,
    views_change: overviewData?.views_change ?? null,
    likes_change: overviewData?.likes_change ?? null,
    comments_change: 0,
    shares_change: 0,
  }

  // Map platform data with safe defaults
  const platformStats: PlatformStats[] = (platformData?.platforms || []).map((p: any) => ({
    platform: p.platform ?? "unknown",
    views: p.views ?? 0,
    likes: p.likes ?? 0,
    comments: p.comments ?? 0,
    shares: p.shares ?? 0,
    posts: p.posts ?? 0,
    engagement_rate: p.engagement_rate ?? 0,
  }))

  // Map time series data
  const timeSeriesPoints = (timeSeriesData?.data_points || timeSeriesData?.data || []).map((d: any) => ({
    date: d.date,
    value: d.value,
  }))

  const isLoading = overviewLoading || platformLoading

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  // Check if there's any data
  const hasData = overview.total_posts > 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
          <p className="text-muted-foreground">
            Track your content performance across platforms
          </p>
        </div>
        <div className="flex gap-2">
          <Select value={period} onValueChange={setPeriod}>
            <SelectTrigger className="w-36">
              <Calendar className="mr-2 h-4 w-4" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
              <SelectItem value="90d">Last 90 days</SelectItem>
              <SelectItem value="1y">Last year</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
          >
            {syncMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            Sync
          </Button>
        </div>
      </div>

      {!hasData ? (
        // Empty State
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <BarChart3 className="h-12 w-12 text-muted-foreground" />
            <h3 className="mt-4 text-lg font-medium">No Analytics Data Yet</h3>
            <p className="mt-2 text-center text-sm text-muted-foreground">
              Connect your social accounts and publish content to see analytics.
            </p>
            <div className="mt-4 flex gap-2">
              <Link to="/social-accounts">
                <Button variant="outline">Connect Accounts</Button>
              </Link>
              <Link to="/create">
                <Button>Create Video</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Overview Stats */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <StatCard
              title="Total Views"
              value={overview.total_views}
              change={overview.views_change}
              icon={<Eye className="h-4 w-4 text-muted-foreground" />}
            />
            <StatCard
              title="Total Likes"
              value={overview.total_likes}
              change={overview.likes_change}
              icon={<Heart className="h-4 w-4 text-muted-foreground" />}
            />
            <StatCard
              title="Total Comments"
              value={overview.total_comments}
              change={overview.comments_change}
              icon={<MessageCircle className="h-4 w-4 text-muted-foreground" />}
            />
            <StatCard
              title="Engagement Rate"
              value={overview.avg_engagement_rate}
              icon={<TrendingUp className="h-4 w-4 text-muted-foreground" />}
              format="percent"
            />
          </div>

          {/* Time Series Chart */}
          <Card>
            <CardHeader>
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <CardTitle>Performance Over Time</CardTitle>
                  <CardDescription>
                    Track your metrics over the selected period
                  </CardDescription>
                </div>
                <Tabs value={timeSeriesMetric} onValueChange={setTimeSeriesMetric}>
                  <TabsList>
                    <TabsTrigger value="views">Views</TabsTrigger>
                    <TabsTrigger value="likes">Likes</TabsTrigger>
                    <TabsTrigger value="comments">Comments</TabsTrigger>
                    <TabsTrigger value="shares">Shares</TabsTrigger>
                  </TabsList>
                </Tabs>
              </div>
            </CardHeader>
            <CardContent>
              {timeSeriesLoading ? (
                <div className="flex h-40 items-center justify-center">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <TimeSeriesChart
                  data={timeSeriesPoints}
                  metric={timeSeriesMetric}
                  color={
                    timeSeriesMetric === "views" ? "bg-blue-500" :
                    timeSeriesMetric === "likes" ? "bg-red-500" :
                    timeSeriesMetric === "comments" ? "bg-green-500" :
                    "bg-purple-500"
                  }
                />
              )}
            </CardContent>
          </Card>

          {/* Platform Breakdown */}
          {platformStats.length > 0 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold">Platform Performance</h2>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {platformStats.map((stats) => (
                  <PlatformCard key={stats.platform} stats={stats} />
                ))}
              </div>
            </div>
          )}

          {/* Top Performing Content */}
          <Card>
            <CardHeader>
              <CardTitle>Top Performing Content</CardTitle>
              <CardDescription>Your best performing posts by views</CardDescription>
            </CardHeader>
            <CardContent>
              {topPerformingLoading ? (
                <div className="flex h-40 items-center justify-center">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : topPerformingData?.items && topPerformingData.items.length > 0 ? (
                <div className="space-y-3">
                  {topPerformingData.items.map((item: any, index: number) => (
                    <TopPerformingItemCard
                      key={item.post_id}
                      item={item}
                      rank={index + 1}
                    />
                  ))}
                </div>
              ) : (
                <div className="text-center text-muted-foreground py-8">
                  <BarChart3 className="mx-auto h-8 w-8 mb-2" />
                  <p>No top performing content yet</p>
                  <p className="text-sm">Publish content to see your top performers</p>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
