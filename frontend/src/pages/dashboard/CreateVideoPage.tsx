/**
 * Create Video Page
 * 
 * Video generation wizard with template selection and topic input.
 */

import { useState, useEffect } from "react"
import { useNavigate, Link, useSearchParams } from "react-router-dom"
import {
  ArrowLeft,
  ArrowRight,
  Sparkles,
  FileText,
  Loader2,
  Check,
  AlertCircle,
  Video,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useAuth, useIsPremium } from "@/contexts/AuthContext"
import { useTemplates } from "@/hooks/useTemplates"
import { useGenerateVideo, useDailyLimit } from "@/hooks/useVideos"
import { useIntegrationReadiness } from "@/hooks/useIntegrations"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import type { Template } from "@/types"
import toast from "react-hot-toast"

// =============================================================================
// Step Components
// =============================================================================

interface TemplateSelectStepProps {
  templates: Template[]
  selectedTemplate: Template | null
  onSelect: (template: Template) => void
}

function TemplateSelectStep({
  templates,
  selectedTemplate,
  onSelect,
}: TemplateSelectStepProps) {
  const systemTemplates = templates.filter((t) => t.is_system)
  const userTemplates = templates.filter((t) => !t.is_system)

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Choose a Template</h2>
        <p className="text-muted-foreground">
          Select a template that matches your content style
        </p>
      </div>

      {/* System Templates */}
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-muted-foreground">
          System Templates
        </h3>
        <div className="grid gap-3 md:grid-cols-2">
          {systemTemplates.map((template) => (
            <button
              key={template.id}
              className={cn(
                "flex flex-col items-start rounded-lg border p-4 text-left transition-all hover:border-primary",
                selectedTemplate?.id === template.id &&
                  "border-primary bg-primary/5 ring-1 ring-primary"
              )}
              onClick={() => onSelect(template)}
            >
              <div className="flex w-full items-center justify-between">
                <span className="font-medium">{template.name}</span>
                {selectedTemplate?.id === template.id && (
                  <Check className="h-4 w-4 text-primary" />
                )}
              </div>
              <span className="mt-1 text-sm text-muted-foreground">
                {template.description}
              </span>
              <div className="mt-2 flex gap-2">
                <span className="rounded bg-muted px-2 py-0.5 text-xs">
                  {template.category}
                </span>
                <span className="rounded bg-muted px-2 py-0.5 text-xs">
                  {template.config.video_structure.duration_seconds}s
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* User Templates */}
      {userTemplates.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-muted-foreground">
            My Templates
          </h3>
          <div className="grid gap-3 md:grid-cols-2">
            {userTemplates.map((template) => (
              <button
                key={template.id}
                className={cn(
                  "flex flex-col items-start rounded-lg border p-4 text-left transition-all hover:border-primary",
                  selectedTemplate?.id === template.id &&
                    "border-primary bg-primary/5 ring-1 ring-primary"
                )}
                onClick={() => onSelect(template)}
              >
                <div className="flex w-full items-center justify-between">
                  <span className="font-medium">{template.name}</span>
                  {selectedTemplate?.id === template.id && (
                    <Check className="h-4 w-4 text-primary" />
                  )}
                </div>
                <span className="mt-1 text-sm text-muted-foreground">
                  {template.description}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

interface TopicInputStepProps {
  topic: string
  customInstructions: string
  onTopicChange: (topic: string) => void
  onInstructionsChange: (instructions: string) => void
  template: Template | null
}

function TopicInputStep({
  topic,
  customInstructions,
  onTopicChange,
  onInstructionsChange,
  template,
}: TopicInputStepProps) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">What's Your Video About?</h2>
        <p className="text-muted-foreground">
          Describe your topic and the AI will generate a script
        </p>
      </div>

      {/* Template Preview */}
      {template && (
        <Card className="bg-muted/50">
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <FileText className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="font-medium">{template.name}</p>
              <p className="text-sm text-muted-foreground">
                {template.config.script_prompt.tone} tone •{" "}
                {template.config.video_structure.duration_seconds}s video
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Topic Input */}
      <div className="space-y-2">
        <Label htmlFor="topic">Topic *</Label>
        <Input
          id="topic"
          placeholder="e.g., 5 productivity tips for remote workers"
          value={topic}
          onChange={(e) => onTopicChange(e.target.value)}
          className="text-lg"
        />
        <p className="text-xs text-muted-foreground">
          Be specific about what you want the video to cover
        </p>
      </div>

      {/* Custom Instructions */}
      <div className="space-y-2">
        <Label htmlFor="instructions">Custom Instructions (Optional)</Label>
        <textarea
          id="instructions"
          placeholder="Add any specific requirements, target audience details, or style preferences..."
          value={customInstructions}
          onChange={(e) => onInstructionsChange(e.target.value)}
          className="flex min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        />
      </div>
    </div>
  )
}

// =============================================================================
// Main Page Component
// =============================================================================

export default function CreateVideoPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { user } = useAuth()
  const isPremium = useIsPremium()

  // Get prompt from URL query parameter
  const initialPrompt = searchParams.get("prompt") || ""

  const [step, setStep] = useState(1)
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null)
  const [topic, setTopic] = useState(initialPrompt)
  const [customInstructions, setCustomInstructions] = useState("")

  // If prompt is provided via URL, auto-advance to step 2 when template is selected
  const hasPrefilledPrompt = initialPrompt.length > 0

  const { data: templatesData, isLoading: templatesLoading } = useTemplates()
  
  // Auto-select first template if prompt is provided
  useEffect(() => {
    if (hasPrefilledPrompt && templatesData?.templates?.length && !selectedTemplate) {
      // Auto-select the first system template
      const systemTemplate = templatesData.templates.find(t => t.is_system)
      if (systemTemplate) {
        setSelectedTemplate(systemTemplate)
      }
    }
  }, [hasPrefilledPrompt, templatesData, selectedTemplate])
  const { data: readinessData } = useIntegrationReadiness()
  const { data: limitData } = useDailyLimit()
  const generateMutation = useGenerateVideo()

  const templates = templatesData?.templates || []
  const isReady = readinessData?.ready ?? false
  const dailyRemaining = limitData?.remaining ?? 0

  const canGenerate = isPremium || dailyRemaining > 0

  const handleGenerate = async () => {
    if (!selectedTemplate || !topic.trim()) {
      toast.error("Please select a template and enter a topic")
      return
    }

    if (!isReady) {
      toast.error("Please configure required integrations first")
      return
    }

    if (!canGenerate) {
      toast.error("You've reached your daily limit. Upgrade to Premium for unlimited videos!")
      return
    }

    try {
      const result = await generateMutation.mutateAsync({
        template_id: selectedTemplate.id,
        topic: topic.trim(),
        custom_instructions: customInstructions.trim() || undefined,
      })
      navigate(`/videos/${result.video.id}`)
    } catch {
      // Error handled by mutation
    }
  }

  // Not ready state
  if (!isReady) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Card className="max-w-md text-center">
          <CardHeader>
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10">
              <AlertCircle className="h-8 w-8 text-destructive" />
            </div>
            <CardTitle>Setup Required</CardTitle>
            <CardDescription>
              You need to configure the required integrations before creating videos.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link to="/integrations">
              <Button>Configure Integrations</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Loading state
  if (templatesLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Create Video</h1>
          <p className="text-muted-foreground">
            Generate an AI-powered video in minutes
          </p>
        </div>
      </div>

      {/* Daily Limit (Free users) */}
      {!isPremium && (
        <Card className="border-primary/20 bg-primary/5">
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex-1">
              <p className="text-sm font-medium">Daily Video Limit</p>
              <div className="mt-2 flex items-center gap-4">
                <Progress
                  value={((limitData?.limit ?? 1) - dailyRemaining) / (limitData?.limit ?? 1) * 100}
                  className="flex-1"
                />
                <span className="text-sm text-muted-foreground">
                  {dailyRemaining}/{limitData?.limit ?? 1} remaining
                </span>
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

      {/* Progress Steps */}
      <div className="flex items-center gap-2">
        <div
          className={cn(
            "flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium",
            step >= 1 ? "bg-primary text-primary-foreground" : "bg-muted"
          )}
        >
          1
        </div>
        <div
          className={cn(
            "h-1 flex-1 rounded",
            step >= 2 ? "bg-primary" : "bg-muted"
          )}
        />
        <div
          className={cn(
            "flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium",
            step >= 2 ? "bg-primary text-primary-foreground" : "bg-muted"
          )}
        >
          2
        </div>
      </div>

      {/* Step Content */}
      <Card>
        <CardContent className="p-6">
          {step === 1 && (
            <TemplateSelectStep
              templates={templates}
              selectedTemplate={selectedTemplate}
              onSelect={setSelectedTemplate}
            />
          )}
          {step === 2 && (
            <TopicInputStep
              topic={topic}
              customInstructions={customInstructions}
              onTopicChange={setTopic}
              onInstructionsChange={setCustomInstructions}
              template={selectedTemplate}
            />
          )}
        </CardContent>
      </Card>

      {/* Navigation */}
      <div className="flex justify-between">
        <Button
          variant="outline"
          onClick={() => setStep(step - 1)}
          disabled={step === 1}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>

        {step === 1 ? (
          <Button
            onClick={() => setStep(2)}
            disabled={!selectedTemplate}
          >
            Next
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        ) : (
          <Button
            onClick={handleGenerate}
            disabled={!topic.trim() || generateMutation.isPending || !canGenerate}
            className="gap-2"
          >
            {generateMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Starting...
              </>
            ) : (
              <>
                <Video className="h-4 w-4" />
                Generate Video
              </>
            )}
          </Button>
        )}
      </div>
    </div>
  )
}
