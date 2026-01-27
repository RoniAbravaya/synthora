/**
 * Analytics Page
 * 
 * View performance analytics across all platforms.
 */

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Eye,
  Heart,
  MessageCircle,
  Share2,
  Clock,
  Youtube,
  Instagram,
  Facebook,
  Music2,
  Loader2,
  Calendar,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react"
import { cn, formatNumber, formatCompactNumber } from "@/lib/utils"
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
import { Link } from "react-router-dom"
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
  change: number
  icon: React.ReactNode
  format?: "number" | "compact" | "percent"
}

function StatCard({ title, value, change, icon, format = "compact" }: StatCardProps) {
  const safeValue = value ?? 0
  const safeChange = change ?? 0
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
              stats.platform === "instagram" ? "bg-gradient-to-r from-purple-500/10 to-pink-500/10" : `${platformColors[stats.platform]}/10`
            )}
          >
            {platformIcons[stats.platform]}
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
// Main Page Component
// =============================================================================

// Helper to convert period string to days number
function periodToDays(period: string): number {
  switch (period) {
    case "7d": return 7
    case "30d": return 30
    case "90d": return 90
    case "1y": return 365
    default: return 30
  }
}

export default function AnalyticsPage() {
  const [period, setPeriod] = useState("7d")
  const [platform, setPlatform] = useState("all")

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

  // Map API response to expected structure with safe defaults
  const overview: AnalyticsOverview = {
    total_views: overviewData?.summary?.views ?? 0,
    total_likes: overviewData?.summary?.likes ?? 0,
    total_comments: overviewData?.summary?.comments ?? 0,
    total_shares: overviewData?.summary?.shares ?? 0,
    total_posts: overviewData?.total_posts ?? 0,
    avg_engagement_rate: overviewData?.summary?.engagement_rate ?? 0,
    views_change: 0, // API doesn't provide change data yet
    likes_change: 0,
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
              change={0}
              icon={<TrendingUp className="h-4 w-4 text-muted-foreground" />}
              format="percent"
            />
          </div>

          {/* Platform Breakdown */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">Platform Performance</h2>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {platformStats.map((stats) => (
                <PlatformCard key={stats.platform} stats={stats} />
              ))}
            </div>
          </div>

          {/* Top Performing Content */}
          <Card>
            <CardHeader>
              <CardTitle>Top Performing Content</CardTitle>
              <CardDescription>Your best performing posts this period</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center text-muted-foreground py-8">
                <BarChart3 className="mx-auto h-8 w-8 mb-2" />
                <p>Detailed analytics charts coming soon</p>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
