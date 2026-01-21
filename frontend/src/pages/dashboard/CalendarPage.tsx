/**
 * Calendar Page
 * 
 * Scheduled posts calendar view with monthly/weekly views.
 */

import { useState, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import {
  ChevronLeft,
  ChevronRight,
  Plus,
  Calendar as CalendarIcon,
  Clock,
  Video,
  Instagram,
  Youtube,
  Facebook,
  Loader2,
} from "lucide-react"
import { cn, formatDate } from "@/lib/utils"
import { postsService } from "@/services/posts"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { Link } from "react-router-dom"

// =============================================================================
// Types
// =============================================================================

interface ScheduledPost {
  id: string
  title: string
  platform: string
  scheduled_at: string
  status: string
  video_id: string
}

// =============================================================================
// Platform Icons
// =============================================================================

const platformIcons: Record<string, React.ReactNode> = {
  youtube: <Youtube className="h-4 w-4 text-red-500" />,
  instagram: <Instagram className="h-4 w-4 text-pink-500" />,
  facebook: <Facebook className="h-4 w-4 text-blue-500" />,
  tiktok: <Video className="h-4 w-4" />,
}

const platformColors: Record<string, string> = {
  youtube: "bg-red-500/10 border-red-500/30",
  instagram: "bg-pink-500/10 border-pink-500/30",
  facebook: "bg-blue-500/10 border-blue-500/30",
  tiktok: "bg-gray-500/10 border-gray-500/30",
}

// =============================================================================
// Calendar Utilities
// =============================================================================

function getDaysInMonth(year: number, month: number) {
  return new Date(year, month + 1, 0).getDate()
}

function getFirstDayOfMonth(year: number, month: number) {
  return new Date(year, month, 1).getDay()
}

function isSameDay(date1: Date, date2: Date) {
  return (
    date1.getFullYear() === date2.getFullYear() &&
    date1.getMonth() === date2.getMonth() &&
    date1.getDate() === date2.getDate()
  )
}

function isToday(date: Date) {
  return isSameDay(date, new Date())
}

// =============================================================================
// Calendar Day Cell
// =============================================================================

interface CalendarDayCellProps {
  date: Date
  posts: ScheduledPost[]
  isCurrentMonth: boolean
}

function CalendarDayCell({ date, posts, isCurrentMonth }: CalendarDayCellProps) {
  const dayPosts = posts.filter((post) => {
    const postDate = new Date(post.scheduled_at)
    return isSameDay(postDate, date)
  })

  return (
    <div
      className={cn(
        "min-h-24 border-r border-b p-1",
        !isCurrentMonth && "bg-muted/30",
        isToday(date) && "bg-primary/5"
      )}
    >
      <div
        className={cn(
          "mb-1 flex h-6 w-6 items-center justify-center rounded-full text-sm",
          isToday(date) && "bg-primary text-primary-foreground"
        )}
      >
        {date.getDate()}
      </div>
      <div className="space-y-1">
        {dayPosts.slice(0, 3).map((post) => (
          <TooltipProvider key={post.id}>
            <Tooltip>
              <TooltipTrigger asChild>
                <Link
                  to={`/dashboard/posts/${post.id}`}
                  className={cn(
                    "flex items-center gap-1 truncate rounded border px-1 py-0.5 text-xs",
                    platformColors[post.platform] || "bg-muted"
                  )}
                >
                  {platformIcons[post.platform]}
                  <span className="truncate">{post.title || "Untitled"}</span>
                </Link>
              </TooltipTrigger>
              <TooltipContent>
                <p className="font-medium">{post.title || "Untitled"}</p>
                <p className="text-xs text-muted-foreground">
                  {formatDate(post.scheduled_at)} • {post.platform}
                </p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        ))}
        {dayPosts.length > 3 && (
          <div className="text-xs text-muted-foreground">
            +{dayPosts.length - 3} more
          </div>
        )}
      </div>
    </div>
  )
}

// =============================================================================
// Monthly Calendar View
// =============================================================================

interface MonthlyCalendarProps {
  year: number
  month: number
  posts: ScheduledPost[]
}

function MonthlyCalendar({ year, month, posts }: MonthlyCalendarProps) {
  const daysInMonth = getDaysInMonth(year, month)
  const firstDayOfMonth = getFirstDayOfMonth(year, month)
  const daysInPrevMonth = getDaysInMonth(year, month - 1)

  const weeks: Date[][] = []
  let currentWeek: Date[] = []

  // Previous month days
  for (let i = firstDayOfMonth - 1; i >= 0; i--) {
    currentWeek.push(new Date(year, month - 1, daysInPrevMonth - i))
  }

  // Current month days
  for (let day = 1; day <= daysInMonth; day++) {
    currentWeek.push(new Date(year, month, day))
    if (currentWeek.length === 7) {
      weeks.push(currentWeek)
      currentWeek = []
    }
  }

  // Next month days
  if (currentWeek.length > 0) {
    let nextDay = 1
    while (currentWeek.length < 7) {
      currentWeek.push(new Date(year, month + 1, nextDay++))
    }
    weeks.push(currentWeek)
  }

  const weekDays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

  return (
    <div className="rounded-lg border">
      {/* Header */}
      <div className="grid grid-cols-7 border-b">
        {weekDays.map((day) => (
          <div
            key={day}
            className="border-r p-2 text-center text-sm font-medium text-muted-foreground last:border-r-0"
          >
            {day}
          </div>
        ))}
      </div>

      {/* Calendar Grid */}
      <div>
        {weeks.map((week, weekIndex) => (
          <div key={weekIndex} className="grid grid-cols-7">
            {week.map((date, dayIndex) => (
              <CalendarDayCell
                key={dayIndex}
                date={date}
                posts={posts}
                isCurrentMonth={date.getMonth() === month}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

// =============================================================================
// Weekly Calendar View
// =============================================================================

interface WeeklyCalendarProps {
  startDate: Date
  posts: ScheduledPost[]
}

function WeeklyCalendar({ startDate, posts }: WeeklyCalendarProps) {
  const weekDays = useMemo(() => {
    const days: Date[] = []
    const start = new Date(startDate)
    start.setDate(start.getDate() - start.getDay()) // Start from Sunday
    
    for (let i = 0; i < 7; i++) {
      const day = new Date(start)
      day.setDate(start.getDate() + i)
      days.push(day)
    }
    return days
  }, [startDate])

  const hours = Array.from({ length: 24 }, (_, i) => i)

  return (
    <div className="rounded-lg border">
      {/* Header */}
      <div className="grid grid-cols-8 border-b">
        <div className="border-r p-2"></div>
        {weekDays.map((date, i) => (
          <div
            key={i}
            className={cn(
              "border-r p-2 text-center last:border-r-0",
              isToday(date) && "bg-primary/5"
            )}
          >
            <div className="text-sm font-medium">
              {date.toLocaleDateString("en-US", { weekday: "short" })}
            </div>
            <div
              className={cn(
                "mx-auto flex h-8 w-8 items-center justify-center rounded-full text-lg",
                isToday(date) && "bg-primary text-primary-foreground"
              )}
            >
              {date.getDate()}
            </div>
          </div>
        ))}
      </div>

      {/* Time Grid */}
      <div className="max-h-[600px] overflow-y-auto">
        {hours.map((hour) => (
          <div key={hour} className="grid grid-cols-8 border-b last:border-b-0">
            <div className="border-r p-1 text-right text-xs text-muted-foreground">
              {hour === 0 ? "12 AM" : hour < 12 ? `${hour} AM` : hour === 12 ? "12 PM" : `${hour - 12} PM`}
            </div>
            {weekDays.map((date, dayIndex) => {
              const dayPosts = posts.filter((post) => {
                const postDate = new Date(post.scheduled_at)
                return isSameDay(postDate, date) && postDate.getHours() === hour
              })

              return (
                <div
                  key={dayIndex}
                  className={cn(
                    "min-h-12 border-r p-1 last:border-r-0",
                    isToday(date) && "bg-primary/5"
                  )}
                >
                  {dayPosts.map((post) => (
                    <Link
                      key={post.id}
                      to={`/dashboard/posts/${post.id}`}
                      className={cn(
                        "mb-1 flex items-center gap-1 truncate rounded border px-1 py-0.5 text-xs",
                        platformColors[post.platform] || "bg-muted"
                      )}
                    >
                      {platformIcons[post.platform]}
                      <span className="truncate">{post.title || "Untitled"}</span>
                    </Link>
                  ))}
                </div>
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}

// =============================================================================
// Upcoming Posts Sidebar
// =============================================================================

interface UpcomingPostsProps {
  posts: ScheduledPost[]
}

function UpcomingPosts({ posts }: UpcomingPostsProps) {
  const upcomingPosts = posts
    .filter((post) => new Date(post.scheduled_at) > new Date())
    .sort((a, b) => new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime())
    .slice(0, 5)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Upcoming Posts</CardTitle>
        <CardDescription>Next 5 scheduled posts</CardDescription>
      </CardHeader>
      <CardContent>
        {upcomingPosts.length === 0 ? (
          <p className="text-sm text-muted-foreground">No upcoming posts scheduled.</p>
        ) : (
          <div className="space-y-3">
            {upcomingPosts.map((post) => (
              <Link
                key={post.id}
                to={`/dashboard/posts/${post.id}`}
                className="flex items-start gap-3 rounded-lg border p-3 transition-colors hover:bg-accent"
              >
                <div className="mt-0.5">{platformIcons[post.platform]}</div>
                <div className="flex-1 space-y-1">
                  <p className="text-sm font-medium leading-none">
                    {post.title || "Untitled"}
                  </p>
                  <p className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    {formatDate(post.scheduled_at)}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// =============================================================================
// Main Page Component
// =============================================================================

export default function CalendarPage() {
  const [view, setView] = useState<"month" | "week">("month")
  const [currentDate, setCurrentDate] = useState(new Date())

  // Fetch scheduled posts
  const { data: postsData, isLoading } = useQuery({
    queryKey: ["posts", "scheduled"],
    queryFn: () => postsService.getScheduled(),
  })

  const posts: ScheduledPost[] = postsData?.posts || []

  // Navigation handlers
  const navigatePrev = () => {
    const newDate = new Date(currentDate)
    if (view === "month") {
      newDate.setMonth(newDate.getMonth() - 1)
    } else {
      newDate.setDate(newDate.getDate() - 7)
    }
    setCurrentDate(newDate)
  }

  const navigateNext = () => {
    const newDate = new Date(currentDate)
    if (view === "month") {
      newDate.setMonth(newDate.getMonth() + 1)
    } else {
      newDate.setDate(newDate.getDate() + 7)
    }
    setCurrentDate(newDate)
  }

  const goToToday = () => {
    setCurrentDate(new Date())
  }

  const monthName = currentDate.toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
  })

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
          <h1 className="text-3xl font-bold tracking-tight">Calendar</h1>
          <p className="text-muted-foreground">
            View and manage your posting schedule
          </p>
        </div>
        <Link to="/dashboard/videos">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Create Video
          </Button>
        </Link>
      </div>

      {/* Calendar Controls */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={navigatePrev}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button variant="outline" onClick={goToToday}>
            Today
          </Button>
          <Button variant="outline" size="icon" onClick={navigateNext}>
            <ChevronRight className="h-4 w-4" />
          </Button>
          <h2 className="ml-2 text-xl font-semibold">{monthName}</h2>
        </div>

        <Tabs value={view} onValueChange={(v) => setView(v as "month" | "week")}>
          <TabsList>
            <TabsTrigger value="month">
              <CalendarIcon className="mr-2 h-4 w-4" />
              Month
            </TabsTrigger>
            <TabsTrigger value="week">
              <Clock className="mr-2 h-4 w-4" />
              Week
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Main Content */}
      <div className="grid gap-6 lg:grid-cols-4">
        <div className="lg:col-span-3">
          {view === "month" ? (
            <MonthlyCalendar
              year={currentDate.getFullYear()}
              month={currentDate.getMonth()}
              posts={posts}
            />
          ) : (
            <WeeklyCalendar startDate={currentDate} posts={posts} />
          )}
        </div>

        <div className="space-y-6">
          <UpcomingPosts posts={posts} />

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Quick Stats</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">This Month</span>
                <span className="font-medium">
                  {posts.filter((p) => {
                    const postDate = new Date(p.scheduled_at)
                    return (
                      postDate.getMonth() === currentDate.getMonth() &&
                      postDate.getFullYear() === currentDate.getFullYear()
                    )
                  }).length}{" "}
                  posts
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Upcoming</span>
                <span className="font-medium">
                  {posts.filter((p) => new Date(p.scheduled_at) > new Date()).length} posts
                </span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
