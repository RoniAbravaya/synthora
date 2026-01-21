/**
 * Dashboard Page
 * 
 * Main dashboard with overview stats and quick actions.
 */

import { Link } from "react-router-dom"
import { Plus, Video, BarChart3, Calendar, ArrowRight, Sparkles } from "lucide-react"
import { useAuth, useIsPremium } from "@/contexts/AuthContext"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"

export default function DashboardPage() {
  const { user } = useAuth()
  const isPremium = useIsPremium()

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
                <Progress value={0} className="flex-1" />
                <span className="text-sm text-muted-foreground">0/1 used</span>
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
            <div className="text-2xl font-bold">0</div>
            <p className="text-xs text-muted-foreground">
              Start creating to see your videos here
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Views</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0</div>
            <p className="text-xs text-muted-foreground">
              Connect social accounts to track
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Scheduled Posts</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0</div>
            <p className="text-xs text-muted-foreground">
              No upcoming posts
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Engagement Rate</CardTitle>
            <Sparkles className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">--%</div>
            <p className="text-xs text-muted-foreground">
              Publish content to see engagement
            </p>
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

