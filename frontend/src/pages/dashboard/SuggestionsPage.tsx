/**
 * Suggestions Page
 * 
 * AI-powered suggestions and recommendations (premium feature).
 */

import { useState } from "react"
import { Link } from "react-router-dom"
import {
  Sparkles,
  Lock,
  Clock,
  Lightbulb,
  TrendingUp,
  AlertTriangle,
  Check,
  X,
  Loader2,
  RefreshCw,
  Bell,
  Calendar,
  Hash,
  Target,
  Zap,
  ChevronRight,
  Eye,
  ThumbsUp,
  Filter,
} from "lucide-react"
import { cn, formatRelativeTime } from "@/lib/utils"
import { useIsPremium } from "@/contexts/AuthContext"
import {
  useSuggestions,
  useMarkSuggestionRead,
  useDismissSuggestion,
  useMarkAllSuggestionsRead,
  useGenerateSuggestions,
  usePostingTimesAnalysis,
  useContentIdeas,
  useTrends,
  useImprovements,
} from "@/hooks/useSuggestions"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

// =============================================================================
// Premium Gate Component
// =============================================================================

function PremiumGate() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <Card className="max-w-md text-center">
        <CardHeader>
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-synthora">
            <Lock className="h-8 w-8 text-white" />
          </div>
          <CardTitle>Premium Feature</CardTitle>
          <CardDescription>
            AI Suggestions is available for Premium users only.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <ul className="space-y-2 text-left text-sm">
            <li className="flex items-center gap-2">
              <Check className="h-4 w-4 text-primary" />
              Optimal posting time recommendations
            </li>
            <li className="flex items-center gap-2">
              <Check className="h-4 w-4 text-primary" />
              AI-generated content ideas
            </li>
            <li className="flex items-center gap-2">
              <Check className="h-4 w-4 text-primary" />
              Trending topic alerts
            </li>
            <li className="flex items-center gap-2">
              <Check className="h-4 w-4 text-primary" />
              Performance improvement tips
            </li>
          </ul>
          <Link to="/settings">
            <Button className="w-full gap-2">
              <Sparkles className="h-4 w-4" />
              Upgrade to Premium
            </Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  )
}

// =============================================================================
// Suggestion Type Icons
// =============================================================================

const suggestionTypeIcons: Record<string, React.ReactNode> = {
  posting_time: <Clock className="h-4 w-4" />,
  content: <Lightbulb className="h-4 w-4" />,
  trend: <TrendingUp className="h-4 w-4" />,
  improvement: <AlertTriangle className="h-4 w-4" />,
  template: <Target className="h-4 w-4" />,
  prediction: <Zap className="h-4 w-4" />,
}

const priorityColors: Record<string, string> = {
  high: "bg-red-500/10 text-red-500 border-red-500/20",
  medium: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
  low: "bg-blue-500/10 text-blue-500 border-blue-500/20",
}

// =============================================================================
// Suggestions List Tab
// =============================================================================

function SuggestionsListTab() {
  const [filter, setFilter] = useState<string>("all")
  const [showRead, setShowRead] = useState(false)
  
  const { data, isLoading, refetch } = useSuggestions({
    type: filter === "all" ? undefined : filter as any,
    include_read: showRead,
    limit: 50,
  })
  
  const markReadMutation = useMarkSuggestionRead()
  const dismissMutation = useDismissSuggestion()
  const markAllReadMutation = useMarkAllSuggestionsRead()
  const generateMutation = useGenerateSuggestions()
  
  const suggestions = data?.suggestions || []
  const unreadCount = data?.unread_count || 0
  
  const handleMarkRead = async (id: string) => {
    await markReadMutation.mutateAsync(id)
  }
  
  const handleDismiss = async (id: string) => {
    await dismissMutation.mutateAsync({ id })
  }
  
  const handleMarkAllRead = async () => {
    await markAllReadMutation.mutateAsync()
  }
  
  const handleGenerate = async () => {
    await generateMutation.mutateAsync()
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Filters and Actions */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-[180px]">
              <Filter className="mr-2 h-4 w-4" />
              <SelectValue placeholder="Filter by type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="posting_time">Posting Time</SelectItem>
              <SelectItem value="content">Content Ideas</SelectItem>
              <SelectItem value="trend">Trends</SelectItem>
              <SelectItem value="improvement">Improvements</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowRead(!showRead)}
            className={cn(showRead && "bg-primary/10")}
          >
            {showRead ? "Hide Read" : "Show Read"}
          </Button>
        </div>
        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleMarkAllRead}
              disabled={markAllReadMutation.isPending}
            >
              <Check className="mr-2 h-4 w-4" />
              Mark All Read
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleGenerate}
            disabled={generateMutation.isPending}
          >
            {generateMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            Generate New
          </Button>
        </div>
      </div>

      {/* Unread Count Badge */}
      {unreadCount > 0 && (
        <div className="flex items-center gap-2 rounded-lg bg-primary/10 p-3">
          <Bell className="h-5 w-5 text-primary" />
          <span className="text-sm">
            You have <strong>{unreadCount}</strong> unread suggestion{unreadCount !== 1 ? "s" : ""}
          </span>
        </div>
      )}

      {/* Suggestions List */}
      {suggestions.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Sparkles className="h-12 w-12 text-muted-foreground" />
            <h3 className="mt-4 text-lg font-medium">No Suggestions Yet</h3>
            <p className="mt-2 text-center text-sm text-muted-foreground">
              Click "Generate New" to get AI-powered recommendations based on your content.
            </p>
            <Button
              className="mt-4"
              onClick={handleGenerate}
              disabled={generateMutation.isPending}
            >
              {generateMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="mr-2 h-4 w-4" />
              )}
              Generate Suggestions
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {suggestions.map((suggestion) => (
            <Card
              key={suggestion.id}
              className={cn(
                "transition-all",
                !suggestion.is_read && "border-primary/50 bg-primary/5"
              )}
            >
              <CardContent className="p-4">
                <div className="flex items-start gap-4">
                  <div className={cn(
                    "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
                    priorityColors[suggestion.priority] || "bg-muted"
                  )}>
                    {suggestionTypeIcons[suggestion.suggestion_type] || <Sparkles className="h-4 w-4" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h4 className="font-medium">{suggestion.title}</h4>
                        <p className="mt-1 text-sm text-muted-foreground">
                          {suggestion.description}
                        </p>
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        {!suggestion.is_read && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleMarkRead(suggestion.id)}
                            disabled={markReadMutation.isPending}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDismiss(suggestion.id)}
                          disabled={dismissMutation.isPending}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                    <div className="mt-2 flex items-center gap-3 text-xs text-muted-foreground">
                      <span className="capitalize">{suggestion.suggestion_type.replace("_", " ")}</span>
                      <span>•</span>
                      <span className="capitalize">{suggestion.priority} priority</span>
                      <span>•</span>
                      <span>{formatRelativeTime(suggestion.created_at)}</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Posting Times Tab
// =============================================================================

function PostingTimesTab() {
  const { data, isLoading, error } = usePostingTimesAnalysis(90)
  
  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }
  
  if (error || !data?.success) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <Clock className="h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-medium">Not Enough Data</h3>
          <p className="mt-2 text-center text-sm text-muted-foreground">
            {data?.error || "You need more published posts to analyze optimal posting times."}
          </p>
          <p className="text-sm text-muted-foreground">
            Posts analyzed: {data?.posts_analyzed || 0}
          </p>
        </CardContent>
      </Card>
    )
  }
  
  const overall = data.overall
  const byPlatform = data.by_platform || {}
  
  const dayNames = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
  const formatHour = (hour: number) => {
    const h = hour % 12 || 12
    const ampm = hour < 12 ? "AM" : "PM"
    return `${h}:00 ${ampm}`
  }

  return (
    <div className="space-y-6">
      {/* Overall Best Time */}
      {overall && (
        <Card className="border-primary/50 bg-primary/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-primary" />
              Best Time to Post
            </CardTitle>
            <CardDescription>
              Based on analysis of {data.posts_analyzed} posts over {data.period_days} days
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-lg bg-background p-4 text-center">
                <Calendar className="mx-auto h-8 w-8 text-primary" />
                <p className="mt-2 text-2xl font-bold">{overall.best_day}</p>
                <p className="text-sm text-muted-foreground">Best Day</p>
              </div>
              <div className="rounded-lg bg-background p-4 text-center">
                <Clock className="mx-auto h-8 w-8 text-primary" />
                <p className="mt-2 text-2xl font-bold">{formatHour(overall.best_hour)}</p>
                <p className="text-sm text-muted-foreground">Best Time</p>
              </div>
              <div className="rounded-lg bg-background p-4 text-center">
                <TrendingUp className="mx-auto h-8 w-8 text-green-500" />
                <p className="mt-2 text-2xl font-bold text-green-500">
                  +{overall.potential_improvement.toFixed(0)}%
                </p>
                <p className="text-sm text-muted-foreground">Potential Improvement</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* By Platform */}
      {Object.keys(byPlatform).length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">By Platform</h3>
          <div className="grid gap-4 md:grid-cols-2">
            {Object.entries(byPlatform).map(([platform, analysis]: [string, any]) => (
              <Card key={platform}>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base capitalize">{platform}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Best Day</span>
                    <span className="font-medium">{analysis.best_day}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Best Time</span>
                    <span className="font-medium">{formatHour(analysis.best_hour)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Avg Engagement</span>
                    <span className="font-medium">{analysis.best_avg_engagement?.toFixed(1)}%</span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Content Ideas Tab
// =============================================================================

function ContentIdeasTab() {
  const { data, isLoading, refetch } = useContentIdeas(5)
  
  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }
  
  const ideas = data?.ideas || []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          AI-generated content ideas based on your performance data
        </p>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {ideas.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Lightbulb className="h-12 w-12 text-muted-foreground" />
            <h3 className="mt-4 text-lg font-medium">No Ideas Available</h3>
            <p className="mt-2 text-center text-sm text-muted-foreground">
              Publish more content to get personalized content ideas.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {ideas.map((idea, index) => (
            <Card key={index} className="hover:border-primary/50 transition-colors">
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Lightbulb className="h-4 w-4 text-yellow-500" />
                  {idea.topic}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">Hook</p>
                  <p className="text-sm italic">"{idea.hook}"</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">Description</p>
                  <p className="text-sm">{idea.description}</p>
                </div>
                {idea.suggested_hashtags.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-1">Hashtags</p>
                    <div className="flex flex-wrap gap-1">
                      {idea.suggested_hashtags.map((tag, i) => (
                        <span
                          key={i}
                          className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-xs"
                        >
                          <Hash className="mr-0.5 h-3 w-3" />
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                <div className="flex items-center justify-between pt-2 border-t">
                  <span className="text-xs text-muted-foreground">Est. Engagement</span>
                  <span className={cn(
                    "text-xs font-medium px-2 py-0.5 rounded-full",
                    idea.estimated_engagement === "high" && "bg-green-500/10 text-green-500",
                    idea.estimated_engagement === "medium" && "bg-yellow-500/10 text-yellow-500",
                    idea.estimated_engagement === "low" && "bg-muted text-muted-foreground"
                  )}>
                    {idea.estimated_engagement}
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Trends Tab
// =============================================================================

function TrendsTab() {
  const { data, isLoading, refetch } = useTrends()
  
  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }
  
  const trends = data?.trends || []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Trending topics matched to your content niche
        </p>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {trends.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <TrendingUp className="h-12 w-12 text-muted-foreground" />
            <h3 className="mt-4 text-lg font-medium">No Trends Available</h3>
            <p className="mt-2 text-center text-sm text-muted-foreground">
              Check back later for trending topics in your niche.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {trends.map((trend, index) => (
            <Card key={index}>
              <CardContent className="p-4">
                <div className="flex items-start gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-gradient-to-r from-purple-500/10 to-pink-500/10">
                    <TrendingUp className="h-5 w-5 text-purple-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <h4 className="font-medium">{trend.topic}</h4>
                      <div className="flex items-center gap-1">
                        <Zap className="h-4 w-4 text-yellow-500" />
                        <span className="text-sm font-medium">{trend.virality_score}/10</span>
                      </div>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {trend.description}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {trend.platforms.map((platform) => (
                        <span
                          key={platform}
                          className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-xs capitalize"
                        >
                          {platform}
                        </span>
                      ))}
                    </div>
                    {trend.suggested_angle && (
                      <div className="mt-3 rounded-lg bg-muted/50 p-2">
                        <p className="text-xs font-medium text-muted-foreground mb-1">
                          Suggested Angle
                        </p>
                        <p className="text-sm">{trend.suggested_angle}</p>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Improvements Tab
// =============================================================================

function ImprovementsTab() {
  const { data, isLoading, refetch } = useImprovements()
  
  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }
  
  const posts = data?.underperforming_posts || []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Suggestions to improve your underperforming content
        </p>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {posts.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <ThumbsUp className="h-12 w-12 text-green-500" />
            <h3 className="mt-4 text-lg font-medium">Great Job!</h3>
            <p className="mt-2 text-center text-sm text-muted-foreground">
              Your content is performing well. No improvements needed at this time.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {posts.map((post) => (
            <Card key={post.post_id}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">
                    {post.title || "Untitled Post"}
                  </CardTitle>
                  <span className="text-sm text-muted-foreground">
                    {post.current_engagement.toFixed(1)}% engagement
                  </span>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {post.improvements.map((improvement, index) => (
                  <div
                    key={index}
                    className={cn(
                      "rounded-lg border p-3",
                      improvement.impact === "high" && "border-red-500/30 bg-red-500/5",
                      improvement.impact === "medium" && "border-yellow-500/30 bg-yellow-500/5",
                      improvement.impact === "low" && "border-blue-500/30 bg-blue-500/5"
                    )}
                  >
                    <div className="flex items-start gap-3">
                      <AlertTriangle className={cn(
                        "h-4 w-4 mt-0.5 shrink-0",
                        improvement.impact === "high" && "text-red-500",
                        improvement.impact === "medium" && "text-yellow-500",
                        improvement.impact === "low" && "text-blue-500"
                      )} />
                      <div>
                        <p className="text-sm font-medium">{improvement.issue}</p>
                        <p className="mt-1 text-sm text-muted-foreground">
                          {improvement.suggestion}
                        </p>
                        <div className="mt-2 flex items-center gap-2">
                          <span className="text-xs capitalize text-muted-foreground">
                            {improvement.category}
                          </span>
                          <span className="text-xs">•</span>
                          <span className={cn(
                            "text-xs capitalize",
                            improvement.impact === "high" && "text-red-500",
                            improvement.impact === "medium" && "text-yellow-500",
                            improvement.impact === "low" && "text-blue-500"
                          )}>
                            {improvement.impact} impact
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Main Page Component
// =============================================================================

export default function SuggestionsPage() {
  const isPremium = useIsPremium()

  if (!isPremium) {
    return <PremiumGate />
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">AI Suggestions</h1>
        <p className="text-muted-foreground">
          Personalized recommendations to improve your content performance
        </p>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="suggestions" className="space-y-6">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="suggestions" className="gap-2">
            <Bell className="h-4 w-4" />
            <span className="hidden sm:inline">Suggestions</span>
          </TabsTrigger>
          <TabsTrigger value="posting-times" className="gap-2">
            <Clock className="h-4 w-4" />
            <span className="hidden sm:inline">Posting Times</span>
          </TabsTrigger>
          <TabsTrigger value="content-ideas" className="gap-2">
            <Lightbulb className="h-4 w-4" />
            <span className="hidden sm:inline">Content Ideas</span>
          </TabsTrigger>
          <TabsTrigger value="trends" className="gap-2">
            <TrendingUp className="h-4 w-4" />
            <span className="hidden sm:inline">Trends</span>
          </TabsTrigger>
          <TabsTrigger value="improvements" className="gap-2">
            <AlertTriangle className="h-4 w-4" />
            <span className="hidden sm:inline">Improvements</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="suggestions">
          <SuggestionsListTab />
        </TabsContent>

        <TabsContent value="posting-times">
          <PostingTimesTab />
        </TabsContent>

        <TabsContent value="content-ideas">
          <ContentIdeasTab />
        </TabsContent>

        <TabsContent value="trends">
          <TrendsTab />
        </TabsContent>

        <TabsContent value="improvements">
          <ImprovementsTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
