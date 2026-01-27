/**
 * Dashboard Page
 * 
 * Main dashboard with overview stats and quick actions.
 * Fetches real data from the API to display video counts, analytics, and scheduled posts.
 */

import { Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { Plus, Video, BarChart3, Calendar, ArrowRight, Sparkles, Loader2 } from "lucide-react"
import { useAuth, useIsPremium } from "@/contexts/AuthContext"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { useVideos, useDailyLimit } from "@/hooks/useVideos"
import { analyticsService } from "@/services/analytics"
import { postsService } from "@/services/posts"
import { formatCompactNumber } from "@/lib/utils"

export default function DashboardPage() {
  const { user } = useAuth()
  const isPremium = useIsPremium()

  // Fetch videos to get total count
  const { data: videosData, isLoading: videosLoading } = useVideos({ limit: 1 })
  
  // Fetch daily limit for free users
  const { data: dailyLimitData, isLoading: dailyLimitLoading } = useDailyLimit()
  
  // Fetch analytics overview
  const { data: analyticsData, isLoading: analyticsLoading } = useQuery({
    queryKey: ["analytics", "overview", 30],
    queryFn: () => analyticsService.getOverview(30),
  })
  
  // Fetch upcoming posts for scheduled posts count
  const { data: upcomingData, isLoading: upcomingLoading } = useQuery({
    queryKey: ["posts", "upcoming"],
    queryFn: () => postsService.getUpcoming(100),
  })

  // Calculate values with safe defaults
  const totalVideos = videosData?.total ?? 0
  const totalViews = analyticsData?.summary?.views ?? 0
  const engagementRate = analyticsData?.summary?.engagement_rate ?? 0
  const scheduledPostsCount = upcomingData?.posts?.filter(
    (p) => p.status === "scheduled" && new Date(p.scheduled_at || "") > new Date()
  ).length ?? 0
  
  // Daily limit values
  const dailyLimitUsed = dailyLimitData?.used ?? 0
  const dailyLimitMax = dailyLimitData?.limit ?? 1
  const dailyLimitProgress = dailyLimitMax > 0 ? (dailyLimitUsed / dailyLimitMax) * 100 : 0
  
  const isLoading = videosLoading || analyticsLoading || upcomingLoading

  return (
    <div className="space-y-8">
      {/* Welcome header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Welcome back, {user?.display_name?.split(" ")[0] || "Creator"}!
          </h1>
          <p className="text-muted-foreground">
            Here's what's happening with your content today.
          </p>
        </div>
        <Link to="/create">
          <Button size="lg" className="gap-2">
            <Plus className="h-4 w-4" />
            Create Video
          </Button>
        </Link>
      </div>

      {/* Usage stats for free users */}
      {!isPremium && (
        <Card className="border-primary/20 bg-primary/5">
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex-1">
              <p className="text-sm font-medium">Daily Video Limit</p>
              <div className="mt-2 flex items-center gap-4">
                {dailyLimitLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                ) : (
                  <>
                    <Progress value={dailyLimitProgress} className="flex-1" />
                    <span className="text-sm text-muted-foreground">
                      {dailyLimitUsed}/{dailyLimitMax} used
                    </span>
                  </>
                )}
              </div>
            </div>
            <Link to="/settings">
              <Button variant="outline" size="sm" className="gap-2">
                <Sparkles className="h-4 w-4" />
                Upgrade
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}

      {/* Quick stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Videos</CardTitle>
            <Video className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            ) : (
              <>
                <div className="text-2xl font-bold">{totalVideos}</div>
                <p className="text-xs text-muted-foreground">
                  {totalVideos === 0 
                    ? "Start creating to see your videos here"
                    : `${totalVideos} video${totalVideos !== 1 ? "s" : ""} generated`
                  }
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Views</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            ) : (
              <>
                <div className="text-2xl font-bold">{formatCompactNumber(totalViews)}</div>
                <p className="text-xs text-muted-foreground">
                  {totalViews === 0 
                    ? "Connect social accounts to track"
                    : "Across all platforms"
                  }
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Scheduled Posts</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            ) : (
              <>
                <div className="text-2xl font-bold">{scheduledPostsCount}</div>
                <p className="text-xs text-muted-foreground">
                  {scheduledPostsCount === 0 
                    ? "No upcoming posts"
                    : `${scheduledPostsCount} post${scheduledPostsCount !== 1 ? "s" : ""} scheduled`
                  }
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Engagement Rate</CardTitle>
            <Sparkles className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            ) : (
              <>
                <div className="text-2xl font-bold">
                  {engagementRate > 0 ? `${engagementRate.toFixed(1)}%` : "--%"}
                </div>
                <p className="text-xs text-muted-foreground">
                  {engagementRate === 0 
                    ? "Publish content to see engagement"
                    : "Average engagement rate"
                  }
                </p>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick actions */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card className="group cursor-pointer transition-colors hover:border-primary/50">
          <Link to="/integrations">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Set Up Integrations
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </CardTitle>
              <CardDescription>
                Connect AI services to start generating videos
              </CardDescription>
            </CardHeader>
          </Link>
        </Card>

        <Card className="group cursor-pointer transition-colors hover:border-primary/50">
          <Link to="/social-accounts">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Connect Social Accounts
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </CardTitle>
              <CardDescription>
                Link YouTube, TikTok, Instagram, and Facebook
              </CardDescription>
            </CardHeader>
          </Link>
        </Card>

        <Card className="group cursor-pointer transition-colors hover:border-primary/50">
          <Link to="/templates">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Explore Templates
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </CardTitle>
              <CardDescription>
                Browse video templates for different content types
              </CardDescription>
            </CardHeader>
          </Link>
        </Card>
      </div>
    </div>
  )
}

