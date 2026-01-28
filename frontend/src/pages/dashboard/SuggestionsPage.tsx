/**
 * Suggestions Page
 *
 * AI-powered suggestions with:
 * - Smart suggestion generation (analytics or trends based)
 * - Interactive chat interface
 * - Video series and monthly plan creation
 * - Direct scheduling capabilities
 */

import { useState, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import {
  Sparkles,
  Lock,
  Check,
  Loader2,
  Bell,
  Clock,
  Lightbulb,
  TrendingUp,
  AlertTriangle,
} from "lucide-react"
import { Link } from "react-router-dom"
import { cn } from "@/lib/utils"
import { useIsPremium } from "@/contexts/AuthContext"
import { useIntegrations } from "@/hooks/useIntegrations"
import {
  useGenerateSmartSuggestion,
  useSuggestions,
} from "@/hooks/useSuggestions"
import { useChatSession, useSendChatMessage, useExecuteAction } from "@/hooks/useAIChat"
import { useScheduleVideo } from "@/hooks/useVideoPlanning"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  AIThinkingIndicator,
  SuggestionCard,
  ChatInterface,
  ScheduleModal,
  OpenAISetupPrompt,
} from "@/components/ai"
import type { AISuggestionData, ChatMessage, ActionCard as ActionCardType } from "@/types"

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
              AI-powered video suggestions
            </li>
            <li className="flex items-center gap-2">
              <Check className="h-4 w-4 text-primary" />
              Interactive chat to refine ideas
            </li>
            <li className="flex items-center gap-2">
              <Check className="h-4 w-4 text-primary" />
              Create video series and monthly plans
            </li>
            <li className="flex items-center gap-2">
              <Check className="h-4 w-4 text-primary" />
              Automatic scheduling and posting
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
// Main Page Component
// =============================================================================

export default function SuggestionsPage() {
  const isPremium = useIsPremium()
  const navigate = useNavigate()

  // State for generated suggestion
  const [currentSuggestion, setCurrentSuggestion] = useState<AISuggestionData | null>(null)
  const [chatSessionId, setChatSessionId] = useState<string | null>(null)
  const [dataSource, setDataSource] = useState<"analytics" | "trends" | null>(null)
  const [showScheduleModal, setShowScheduleModal] = useState(false)
  const [activeTab, setActiveTab] = useState("generate")

  // Check OpenAI integration
  const { data: integrationsData, isLoading: integrationsLoading } = useIntegrations()
  const hasOpenAI = integrationsData?.integrations?.some(
    (i) => i.provider === "openai" && i.is_active && i.is_valid
  )

  // Generate smart suggestion mutation
  const generateMutation = useGenerateSmartSuggestion()

  // Chat session query
  const { data: chatSession } = useChatSession(chatSessionId)

  // Chat mutations
  const sendMessageMutation = useSendChatMessage(chatSessionId || "")
  const executeActionMutation = useExecuteAction(chatSessionId || "")

  // Schedule mutation
  const scheduleVideoMutation = useScheduleVideo()

  // Premium check
  if (!isPremium) {
    return <PremiumGate />
  }

  // Loading integrations
  if (integrationsLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  // OpenAI not configured
  if (!hasOpenAI) {
    return <OpenAISetupPrompt />
  }

  // Generate suggestion handler
  const handleGenerateSuggestion = async () => {
    try {
      const result = await generateMutation.mutateAsync()
      setCurrentSuggestion(result.suggestion)
      setChatSessionId(result.chat_session_id)
      setDataSource(result.data_source)
      setActiveTab("generate") // Stay on generate tab
    } catch (error) {
      console.error("Failed to generate suggestion:", error)
    }
  }

  // Chat message handler
  const handleSendMessage = async (message: string) => {
    if (!chatSessionId) return
    try {
      await sendMessageMutation.mutateAsync(message)
    } catch (error) {
      console.error("Failed to send message:", error)
    }
  }

  // Execute action handler
  const handleExecuteAction = async (card: ActionCardType) => {
    if (!chatSessionId) return
    
    try {
      const result = await executeActionMutation.mutateAsync({
        action_type: card.type,
        action_data: card.data,
      })
      
      if (result.redirect_url) {
        navigate(result.redirect_url)
      }
    } catch (error) {
      console.error("Failed to execute action:", error)
    }
  }

  // Schedule handler
  const handleSchedule = async (scheduledTime: string, platforms: string[]) => {
    if (!currentSuggestion) return
    
    try {
      await scheduleVideoMutation.mutateAsync({
        suggestion_data: currentSuggestion,
        scheduled_post_time: scheduledTime,
        target_platforms: platforms,
      })
      setShowScheduleModal(false)
      // Show success message or redirect to calendar
    } catch (error) {
      console.error("Failed to schedule video:", error)
    }
  }

  // Generate video handler
  const handleGenerateVideo = () => {
    if (!currentSuggestion) return
    // Navigate to create page with suggestion data
    const params = new URLSearchParams()
    params.set("title", currentSuggestion.title)
    params.set("prompt", currentSuggestion.description)
    navigate(`/create?${params.toString()}`)
  }

  // Refine handler - scroll to chat
  const handleRefine = () => {
    // Chat is already visible when suggestion is generated
    // Just focus on input
  }

  // Convert chat session messages to ChatMessage array
  const messages: ChatMessage[] = chatSession?.messages || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">AI Suggestions</h1>
          <p className="text-muted-foreground">
            Get personalized video ideas powered by AI
          </p>
        </div>
        {!currentSuggestion && (
          <Button
            onClick={handleGenerateSuggestion}
            disabled={generateMutation.isPending}
            size="lg"
          >
            {generateMutation.isPending ? (
              <AIThinkingIndicator text="Generating..." />
            ) : (
              <>
                <Sparkles className="mr-2 h-5 w-5" />
                Generate Suggestion
              </>
            )}
          </Button>
        )}
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="generate" className="gap-2">
            <Sparkles className="h-4 w-4" />
            <span className="hidden sm:inline">AI Generate</span>
          </TabsTrigger>
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
        </TabsList>

        {/* AI Generate Tab */}
        <TabsContent value="generate" className="space-y-6">
          {/* Loading State */}
          {generateMutation.isPending && !currentSuggestion && (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <AIThinkingIndicator className="mb-4" />
                <p className="text-muted-foreground">
                  Analyzing your data and generating a personalized suggestion...
                </p>
              </CardContent>
            </Card>
          )}

          {/* Empty State */}
          {!generateMutation.isPending && !currentSuggestion && (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Sparkles className="h-12 w-12 text-muted-foreground" />
                <h3 className="mt-4 text-lg font-medium">Ready to Generate</h3>
                <p className="mt-2 text-center text-sm text-muted-foreground max-w-md">
                  Click "Generate Suggestion" to get an AI-powered video idea based on
                  your analytics or current trends.
                </p>
                <Button
                  className="mt-4"
                  onClick={handleGenerateSuggestion}
                  disabled={generateMutation.isPending}
                >
                  <Sparkles className="mr-2 h-4 w-4" />
                  Generate Suggestion
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Suggestion Card */}
          {currentSuggestion && dataSource && (
            <SuggestionCard
              suggestion={currentSuggestion}
              dataSource={dataSource}
              onGenerateAnother={handleGenerateSuggestion}
              onGenerateVideo={handleGenerateVideo}
              onSchedule={() => setShowScheduleModal(true)}
              onRefine={handleRefine}
              isGenerating={generateMutation.isPending}
            />
          )}

          {/* Chat Interface */}
          {currentSuggestion && chatSessionId && (
            <ChatInterface
              messages={messages}
              isLoading={sendMessageMutation.isPending}
              onSendMessage={handleSendMessage}
              onExecuteAction={handleExecuteAction}
              suggestion={currentSuggestion}
            />
          )}
        </TabsContent>

        {/* Other tabs - keep existing functionality */}
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
      </Tabs>

      {/* Schedule Modal */}
      {currentSuggestion && (
        <ScheduleModal
          open={showScheduleModal}
          onClose={() => setShowScheduleModal(false)}
          onSchedule={handleSchedule}
          suggestion={currentSuggestion}
          isLoading={scheduleVideoMutation.isPending}
        />
      )}
    </div>
  )
}

// =============================================================================
// Existing Tab Components (Simplified)
// =============================================================================

function SuggestionsListTab() {
  const { data, isLoading } = useSuggestions({
    include_read: false,
    limit: 20,
  })

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  const suggestions = data?.suggestions || []

  if (suggestions.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <Bell className="h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-medium">No Suggestions</h3>
          <p className="mt-2 text-center text-sm text-muted-foreground">
            Use the "AI Generate" tab to get personalized suggestions.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-3">
      {suggestions.map((suggestion) => (
        <Card key={suggestion.id} className={cn(!suggestion.is_read && "border-primary/50")}>
          <CardContent className="p-4">
            <h4 className="font-medium">{suggestion.title}</h4>
            <p className="mt-1 text-sm text-muted-foreground">{suggestion.description}</p>
            <p className="mt-2 text-xs text-muted-foreground capitalize">
              {suggestion.suggestion_type.replace("_", " ")} • {suggestion.priority} priority
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function PostingTimesTab() {
  return (
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-12">
        <Clock className="h-12 w-12 text-muted-foreground" />
        <h3 className="mt-4 text-lg font-medium">Posting Times Analysis</h3>
        <p className="mt-2 text-center text-sm text-muted-foreground">
          Optimal posting time recommendations based on your analytics.
        </p>
      </CardContent>
    </Card>
  )
}

function ContentIdeasTab() {
  return (
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-12">
        <Lightbulb className="h-12 w-12 text-muted-foreground" />
        <h3 className="mt-4 text-lg font-medium">Content Ideas</h3>
        <p className="mt-2 text-center text-sm text-muted-foreground">
          AI-generated content ideas based on your performance data.
        </p>
      </CardContent>
    </Card>
  )
}

function TrendsTab() {
  return (
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-12">
        <TrendingUp className="h-12 w-12 text-muted-foreground" />
        <h3 className="mt-4 text-lg font-medium">Trending Topics</h3>
        <p className="mt-2 text-center text-sm text-muted-foreground">
          Trending topics matched to your content niche.
        </p>
      </CardContent>
    </Card>
  )
}
