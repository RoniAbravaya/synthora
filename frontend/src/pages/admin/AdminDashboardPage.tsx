/**
 * Admin Dashboard Page
 * 
 * Platform statistics, revenue metrics, and admin overview.
 */

import { useState } from "react"
import { Link } from "react-router-dom"
import {
  Users,
  Video,
  Send,
  DollarSign,
  TrendingUp,
  ArrowRight,
  RefreshCw,
  Loader2,
  Crown,
  Activity,
  BarChart3,
} from "lucide-react"
import { cn, formatNumber, formatCurrency, formatRelativeTime } from "@/lib/utils"
import {
  useAdminStats,
  useAdminActivityStats,
  useAdminTopUsers,
} from "@/hooks/useAdmin"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"

// =============================================================================
// Stats Cards
// =============================================================================

interface StatCardProps {
  title: string
  value: string | number
  description?: string
  icon: React.ReactNode
  trend?: { value: number; label: string }
  className?: string
}

function StatCard({ title, value, description, icon, trend, className }: StatCardProps) {
  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {icon}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {description && (
          <p className="text-xs text-muted-foreground">{description}</p>
        )}
        {trend && (
          <p className={cn(
            "mt-1 flex items-center gap-1 text-xs",
            trend.value > 0 ? "text-green-500" : trend.value < 0 ? "text-red-500" : "text-muted-foreground"
          )}>
            {trend.value > 0 ? "+" : ""}{trend.value}% {trend.label}
          </p>
        )}
      </CardContent>
    </Card>
  )
}

// =============================================================================
// Activity Chart (Simple Bar Chart)
// =============================================================================

interface ActivityChartProps {
  data: Array<{ date: string; count: number }>
  label: string
  color?: string
}

function ActivityChart({ data, label, color = "bg-primary" }: ActivityChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
        No data available
      </div>
    )
  }

  const maxValue = Math.max(...data.map(d => d.count), 1)

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className="text-muted-foreground">
          Total: {formatNumber(data.reduce((sum, d) => sum + d.count, 0))}
        </span>
      </div>
      <div className="flex h-24 items-end gap-1">
        {data.slice(-30).map((d, i) => (
          <div
            key={i}
            className="group relative flex-1"
          >
            <div
              className={cn("w-full rounded-t transition-all hover:opacity-80", color)}
              style={{ height: `${Math.max((d.count / maxValue) * 100, 2)}%` }}
            />
            <div className="absolute -top-8 left-1/2 -translate-x-1/2 rounded bg-popover px-2 py-1 text-xs opacity-0 shadow-md transition-opacity group-hover:opacity-100 whitespace-nowrap z-10">
              {d.date}: {d.count}
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
// Top Users List
// =============================================================================

interface TopUsersListProps {
  users: Array<{
    user_id: string
    email: string
    display_name: string | null
    role: string
    count: number
  }>
  metric: string
}

function TopUsersList({ users, metric }: TopUsersListProps) {
  if (!users || users.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
        No users yet
      </div>
    )
  }

  const maxCount = Math.max(...users.map(u => u.count), 1)

  return (
    <div className="space-y-3">
      {users.map((user, index) => (
        <div key={user.user_id} className="flex items-center gap-3">
          <span className="w-6 text-center text-sm font-medium text-muted-foreground">
            {index + 1}
          </span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <p className="truncate text-sm font-medium">
                {user.display_name || user.email}
              </p>
              {user.role === "admin" && (
                <Crown className="h-3 w-3 text-purple-500" />
              )}
              {user.role === "premium" && (
                <Crown className="h-3 w-3 text-primary" />
              )}
            </div>
            <Progress
              value={(user.count / maxCount) * 100}
              className="mt-1 h-1"
            />
          </div>
          <span className="text-sm font-medium">{user.count}</span>
        </div>
      ))}
    </div>
  )
}

// =============================================================================
// Role Distribution
// =============================================================================

interface RoleDistributionProps {
  byRole: Record<string, number>
  total: number
}

function RoleDistribution({ byRole, total }: RoleDistributionProps) {
  const roles = [
    { key: "admin", label: "Admin", color: "bg-purple-500" },
    { key: "premium", label: "Premium", color: "bg-primary" },
    { key: "free", label: "Free", color: "bg-muted-foreground" },
  ]

  return (
    <div className="space-y-3">
      {roles.map(({ key, label, color }) => {
        const count = byRole[key] || 0
        const percentage = total > 0 ? (count / total) * 100 : 0

        return (
          <div key={key} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-2">
                <span className={cn("h-2 w-2 rounded-full", color)} />
                {label}
              </span>
              <span className="text-muted-foreground">
                {count} ({percentage.toFixed(1)}%)
              </span>
            </div>
            <Progress value={percentage} className={cn("h-1.5", `[&>div]:${color}`)} />
          </div>
        )
      })}
    </div>
  )
}

// =============================================================================
// Main Page Component
// =============================================================================

export default function AdminDashboardPage() {
  const [activityDays, setActivityDays] = useState(30)
  const [topUsersMetric, setTopUsersMetric] = useState<"videos" | "posts">("videos")

  const { data: stats, isLoading: statsLoading, refetch: refetchStats } = useAdminStats()
  const { data: activityStats, isLoading: activityLoading } = useAdminActivityStats(activityDays)
  const { data: topUsersData, isLoading: topUsersLoading } = useAdminTopUsers(topUsersMetric, 5)

  const isLoading = statsLoading

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  const platformStats = stats || {
    users: { total: 0, active: 0, new_30d: 0, by_role: {} },
    videos: { total: 0, by_status: {} },
    posts: { total: 0, by_status: {} },
    subscriptions: { total: 0, active: 0, by_plan: {}, mrr: 0, arr: 0 },
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Admin Dashboard</h1>
          <p className="text-muted-foreground">
            Platform overview and statistics
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => refetchStats()}
          className="gap-2"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Users"
          value={formatNumber(platformStats.users.total)}
          description={`${platformStats.users.active} active, ${platformStats.users.new_30d} new this month`}
          icon={<Users className="h-4 w-4 text-muted-foreground" />}
        />
        <StatCard
          title="Total Videos"
          value={formatNumber(platformStats.videos.total)}
          description={`${platformStats.videos.by_status.completed || 0} completed`}
          icon={<Video className="h-4 w-4 text-muted-foreground" />}
        />
        <StatCard
          title="Total Posts"
          value={formatNumber(platformStats.posts.total)}
          description={`${platformStats.posts.by_status.published || 0} published`}
          icon={<Send className="h-4 w-4 text-muted-foreground" />}
        />
        <StatCard
          title="Active Subscriptions"
          value={formatNumber(platformStats.subscriptions.active)}
          description={`of ${platformStats.subscriptions.total} total`}
          icon={<Crown className="h-4 w-4 text-muted-foreground" />}
        />
      </div>

      {/* Revenue Metrics */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="border-green-500/20 bg-green-500/5">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Monthly Recurring Revenue</CardTitle>
            <DollarSign className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-500">
              {formatCurrency(platformStats.subscriptions.mrr)}
            </div>
            <p className="text-xs text-muted-foreground">
              From {platformStats.subscriptions.active} active subscribers
            </p>
          </CardContent>
        </Card>

        <Card className="border-blue-500/20 bg-blue-500/5">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Annual Recurring Revenue</CardTitle>
            <TrendingUp className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-blue-500">
              {formatCurrency(platformStats.subscriptions.arr)}
            </div>
            <p className="text-xs text-muted-foreground">
              Projected annual revenue
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Subscription Distribution */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-4 w-4" />
              User Roles Distribution
            </CardTitle>
            <CardDescription>
              Breakdown of users by account type
            </CardDescription>
          </CardHeader>
          <CardContent>
            <RoleDistribution
              byRole={platformStats.users.by_role}
              total={platformStats.users.total}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Crown className="h-4 w-4" />
              Subscription Plans
            </CardTitle>
            <CardDescription>
              Active subscribers by plan
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[
                { key: "monthly", label: "Monthly ($5/mo)", color: "bg-primary" },
                { key: "annual", label: "Annual ($50/yr)", color: "bg-green-500" },
              ].map(({ key, label, color }) => {
                const count = platformStats.subscriptions.by_plan[key] || 0
                const total = platformStats.subscriptions.active || 1
                const percentage = (count / total) * 100

                return (
                  <div key={key} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className="flex items-center gap-2">
                        <span className={cn("h-2 w-2 rounded-full", color)} />
                        {label}
                      </span>
                      <span className="text-muted-foreground">
                        {count} subscribers
                      </span>
                    </div>
                    <Progress value={percentage} className="h-1.5" />
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Activity Charts */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-4 w-4" />
                Platform Activity
              </CardTitle>
              <CardDescription>
                User signups, videos, and posts over time
              </CardDescription>
            </div>
            <Tabs value={String(activityDays)} onValueChange={(v) => setActivityDays(Number(v))}>
              <TabsList>
                <TabsTrigger value="7">7 days</TabsTrigger>
                <TabsTrigger value="30">30 days</TabsTrigger>
                <TabsTrigger value="90">90 days</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </CardHeader>
        <CardContent>
          {activityLoading ? (
            <div className="flex h-32 items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <div className="grid gap-6 md:grid-cols-3">
              <ActivityChart
                data={activityStats?.daily_signups || []}
                label="User Signups"
                color="bg-blue-500"
              />
              <ActivityChart
                data={activityStats?.daily_videos || []}
                label="Videos Created"
                color="bg-purple-500"
              />
              <ActivityChart
                data={activityStats?.daily_posts || []}
                label="Posts Published"
                color="bg-green-500"
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Top Users & Quick Links */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-4 w-4" />
                  Top Users
                </CardTitle>
                <CardDescription>
                  Most active users by content created
                </CardDescription>
              </div>
              <Tabs value={topUsersMetric} onValueChange={(v) => setTopUsersMetric(v as "videos" | "posts")}>
                <TabsList>
                  <TabsTrigger value="videos">Videos</TabsTrigger>
                  <TabsTrigger value="posts">Posts</TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
          </CardHeader>
          <CardContent>
            {topUsersLoading ? (
              <div className="flex h-32 items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <TopUsersList
                users={topUsersData?.users || []}
                metric={topUsersMetric}
              />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>
              Common admin tasks
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Link to="/admin/users">
              <Button variant="outline" className="w-full justify-between">
                <span className="flex items-center gap-2">
                  <Users className="h-4 w-4" />
                  Manage Users
                </span>
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link to="/admin/settings">
              <Button variant="outline" className="w-full justify-between">
                <span className="flex items-center gap-2">
                  <Activity className="h-4 w-4" />
                  System Settings
                </span>
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link to="/templates">
              <Button variant="outline" className="w-full justify-between">
                <span className="flex items-center gap-2">
                  <Video className="h-4 w-4" />
                  Manage Templates
                </span>
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* Video & Post Status Breakdown */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Video className="h-4 w-4" />
              Video Status
            </CardTitle>
            <CardDescription>
              Videos by generation status
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Object.entries(platformStats.videos.by_status || {}).map(([status, count]) => (
                <div key={status} className="flex items-center justify-between text-sm">
                  <span className="capitalize">{status.replace(/_/g, " ")}</span>
                  <span className="font-medium">{count}</span>
                </div>
              ))}
              {Object.keys(platformStats.videos.by_status || {}).length === 0 && (
                <p className="text-sm text-muted-foreground">No videos yet</p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Send className="h-4 w-4" />
              Post Status
            </CardTitle>
            <CardDescription>
              Posts by publishing status
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Object.entries(platformStats.posts.by_status || {}).map(([status, count]) => (
                <div key={status} className="flex items-center justify-between text-sm">
                  <span className="capitalize">{status}</span>
                  <span className="font-medium">{count}</span>
                </div>
              ))}
              {Object.keys(platformStats.posts.by_status || {}).length === 0 && (
                <p className="text-sm text-muted-foreground">No posts yet</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
