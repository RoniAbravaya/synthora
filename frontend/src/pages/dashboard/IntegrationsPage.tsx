/**
 * Integrations Page
 * 
 * Manage AI service integrations with API keys.
 */

import { useState } from "react"
import {
  Key,
  Plus,
  Check,
  X,
  Eye,
  EyeOff,
  RefreshCw,
  Trash2,
  ExternalLink,
  AlertCircle,
  CheckCircle2,
  Loader2,
} from "lucide-react"
import { cn } from "@/lib/utils"
import {
  useIntegrations,
  useAvailableIntegrations,
  useAddIntegration,
  useDeleteIntegration,
  useValidateIntegration,
  useToggleIntegration,
  useIntegrationReadiness,
} from "@/hooks/useIntegrations"
import { integrationsService } from "@/services/integrations"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Progress } from "@/components/ui/progress"
import type { Integration, AvailableIntegration, IntegrationCategory } from "@/types"
import toast from "react-hot-toast"

// =============================================================================
// Category Display Names & Icons
// =============================================================================

const categoryNames: Record<string, string> = {
  script: "Script Generation",
  voice: "Voice Generation",
  media: "Stock Media",
  video_ai: "AI Video Generation",
  assembly: "Video Assembly",
}

const categoryIcons: Record<string, string> = {
  script: "📝",
  voice: "🎙️",
  media: "🖼️",
  video_ai: "🎬",
  assembly: "🎞️",
}

// Provider info for display
const providerInfo: Record<string, { name: string; description: string; docsUrl: string }> = {
  openai: {
    name: "OpenAI",
    description: "GPT-4 for script generation and content creation",
    docsUrl: "https://platform.openai.com/api-keys",
  },
  anthropic: {
    name: "Anthropic",
    description: "Claude AI for script generation",
    docsUrl: "https://console.anthropic.com/",
  },
  elevenlabs: {
    name: "ElevenLabs",
    description: "High-quality AI voice generation",
    docsUrl: "https://elevenlabs.io/app/api-keys",
  },
  playht: {
    name: "Play.ht",
    description: "Natural AI voice synthesis",
    docsUrl: "https://play.ht/studio/api-access",
  },
  pexels: {
    name: "Pexels",
    description: "Free stock photos and videos",
    docsUrl: "https://www.pexels.com/api/",
  },
  pixabay: {
    name: "Pixabay",
    description: "Free images and videos",
    docsUrl: "https://pixabay.com/api/docs/",
  },
  runway: {
    name: "Runway",
    description: "AI video generation and editing",
    docsUrl: "https://runwayml.com/api",
  },
  heygen: {
    name: "HeyGen",
    description: "AI avatar video generation",
    docsUrl: "https://heygen.com",
  },
  remotion: {
    name: "Remotion",
    description: "Programmatic video creation",
    docsUrl: "https://www.remotion.dev/docs/",
  },
}

// =============================================================================
// Integration Card Component
// =============================================================================

interface IntegrationCardProps {
  integration: Integration
  onDelete: () => void
  onValidate: () => void
  onToggle: (active: boolean) => void
  isValidating: boolean
}

function IntegrationCard({
  integration,
  onDelete,
  onValidate,
  onToggle,
  isValidating,
}: IntegrationCardProps) {
  const [showKey, setShowKey] = useState(false)
  const [fullKey, setFullKey] = useState<string | null>(null)
  const [isRevealing, setIsRevealing] = useState(false)

  const handleRevealKey = async () => {
    if (fullKey) {
      setShowKey(!showKey)
      return
    }

    setIsRevealing(true)
    try {
      const response = await integrationsService.revealKey(integration.id)
      setFullKey(response.api_key)
      setShowKey(true)
    } catch {
      toast.error("Failed to reveal API key")
    } finally {
      setIsRevealing(false)
    }
  }

  const info = providerInfo[integration.provider] || { name: integration.provider, description: "" }

  return (
    <Card className={cn(!integration.is_active && "opacity-60")}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-lg",
                integration.is_valid ? "bg-green-500/10" : "bg-destructive/10"
              )}
            >
              {integration.is_valid ? (
                <CheckCircle2 className="h-5 w-5 text-green-500" />
              ) : (
                <AlertCircle className="h-5 w-5 text-destructive" />
              )}
            </div>
            <div>
              <CardTitle className="text-base">{info.name}</CardTitle>
              <CardDescription className="text-xs">
                {categoryNames[integration.category] || integration.category}
              </CardDescription>
            </div>
          </div>
          <Switch
            checked={integration.is_active}
            onCheckedChange={onToggle}
          />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* API Key */}
        <div className="space-y-2">
          <Label className="text-xs text-muted-foreground">API Key</Label>
          <div className="flex items-center gap-2">
            <Input
              type={showKey ? "text" : "password"}
              value={showKey && fullKey ? fullKey : integration.api_key_masked}
              readOnly
              className="font-mono text-sm"
            />
            <Button
              variant="ghost"
              size="icon"
              onClick={handleRevealKey}
              disabled={isRevealing}
            >
              {isRevealing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : showKey ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>

        {/* Status */}
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Status</span>
          <span
            className={cn(
              "flex items-center gap-1",
              integration.is_valid ? "text-green-500" : "text-destructive"
            )}
          >
            {integration.is_valid ? (
              <>
                <Check className="h-3 w-3" /> Valid
              </>
            ) : (
              <>
                <X className="h-3 w-3" /> Invalid
              </>
            )}
          </span>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={onValidate}
            disabled={isValidating}
          >
            {isValidating ? (
              <Loader2 className="mr-2 h-3 w-3 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-3 w-3" />
            )}
            Validate
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={onDelete}
            className="text-destructive hover:text-destructive"
          >
            <Trash2 className="h-3 w-3" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

// =============================================================================
// Add Integration Dialog
// =============================================================================

interface AddIntegrationDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  availableIntegrations: AvailableIntegration[]
  existingProviders: string[]
}

function AddIntegrationDialog({
  open,
  onOpenChange,
  availableIntegrations,
  existingProviders,
}: AddIntegrationDialogProps) {
  const [selectedProvider, setSelectedProvider] = useState<AvailableIntegration | null>(null)
  const [apiKey, setApiKey] = useState("")
  const addMutation = useAddIntegration()

  const handleAdd = async () => {
    if (!selectedProvider || !apiKey.trim()) return

    try {
      await addMutation.mutateAsync({
        provider: selectedProvider.provider,
        api_key: apiKey.trim(),
      })

      setSelectedProvider(null)
      setApiKey("")
      onOpenChange(false)
      toast.success("Integration added successfully!")
    } catch {
      toast.error("Failed to add integration")
    }
  }

  const filteredIntegrations = availableIntegrations.filter(
    (i) => !existingProviders.includes(i.provider)
  )

  // Group by category
  const groupedIntegrations = filteredIntegrations.reduce(
    (acc, integration) => {
      const cat = integration.category as string
      if (!acc[cat]) {
        acc[cat] = []
      }
      acc[cat].push(integration)
      return acc
    },
    {} as Record<string, AvailableIntegration[]>
  )

  const getProviderInfo = (provider: string) => {
    return providerInfo[provider] || { name: provider, description: "", docsUrl: "" }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Add Integration</DialogTitle>
          <DialogDescription>
            Connect an AI service to enable video generation features.
          </DialogDescription>
        </DialogHeader>

        {!selectedProvider ? (
          <div className="max-h-96 space-y-4 overflow-y-auto">
            {Object.entries(groupedIntegrations).map(([category, integrations]) => (
              <div key={category}>
                <h4 className="mb-2 flex items-center gap-2 text-sm font-medium">
                  <span>{categoryIcons[category] || "🔧"}</span>
                  {categoryNames[category] || category}
                </h4>
                <div className="grid gap-2">
                  {integrations.map((integration) => {
                    const info = getProviderInfo(integration.provider)
                    return (
                      <button
                        key={integration.provider}
                        className="flex items-center justify-between rounded-lg border p-3 text-left transition-colors hover:bg-accent"
                        onClick={() => setSelectedProvider(integration)}
                      >
                        <div>
                          <p className="font-medium">{info.name}</p>
                          <p className="text-sm text-muted-foreground">
                            {info.description}
                          </p>
                        </div>
                        {integration.required && (
                          <span className="rounded bg-primary/10 px-2 py-0.5 text-xs text-primary">
                            Required
                          </span>
                        )}
                      </button>
                    )
                  })}
                </div>
              </div>
            ))}
            {Object.keys(groupedIntegrations).length === 0 && (
              <div className="py-8 text-center text-muted-foreground">
                All available integrations have been configured.
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="rounded-lg border p-4">
              <h4 className="font-medium">{getProviderInfo(selectedProvider.provider).name}</h4>
              <p className="text-sm text-muted-foreground">
                {getProviderInfo(selectedProvider.provider).description}
              </p>
              {getProviderInfo(selectedProvider.provider).docsUrl && (
                <a
                  href={getProviderInfo(selectedProvider.provider).docsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 inline-flex items-center gap-1 text-sm text-primary hover:underline"
                >
                  Get API Key <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="api-key">API Key</Label>
              <Input
                id="api-key"
                type="password"
                placeholder="Enter your API key"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
            </div>
          </div>
        )}

        <DialogFooter>
          {selectedProvider ? (
            <>
              <Button variant="outline" onClick={() => setSelectedProvider(null)}>
                Back
              </Button>
              <Button
                onClick={handleAdd}
                disabled={!apiKey.trim() || addMutation.isPending}
              >
                {addMutation.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Add Integration
              </Button>
            </>
          ) : (
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// =============================================================================
// Main Page Component
// =============================================================================

export default function IntegrationsPage() {
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<string>("all")

  const { data: integrationsData, isLoading: integrationsLoading } = useIntegrations()
  const { data: availableData, isLoading: availableLoading } = useAvailableIntegrations()
  const { data: readinessData } = useIntegrationReadiness()

  const deleteMutation = useDeleteIntegration()
  const validateMutation = useValidateIntegration()
  const toggleMutation = useToggleIntegration()

  // Safely extract data with defaults
  const integrations = integrationsData?.integrations || []
  const availableIntegrations = availableData?.integrations || []
  
  // Categories from backend is a dict: { category_key: display_name }
  const categoriesDict = availableData?.categories || {}
  const categoryKeys = Object.keys(categoriesDict)

  const existingProviders = integrations.map((i) => i.provider)

  // Filter integrations by category
  const filteredIntegrations =
    activeTab === "all"
      ? integrations
      : integrations.filter((i) => i.category === activeTab)

  // Calculate readiness progress
  const configuredCategories = readinessData?.configured_categories || []
  const missingCategories = readinessData?.missing_categories || []
  const totalRequired = 4 // Minimum required categories
  const readinessProgress = (configuredCategories.length / totalRequired) * 100

  if (integrationsLoading || availableLoading) {
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
          <h1 className="text-3xl font-bold tracking-tight">Integrations</h1>
          <p className="text-muted-foreground">
            Connect AI services to enable video generation
          </p>
        </div>
        <Button onClick={() => setAddDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Add Integration
        </Button>
      </div>

      {/* Readiness Card */}
      <Card className={cn(readinessData?.ready ? "border-green-500/50" : "border-primary/50")}>
        <CardContent className="flex items-center gap-4 p-4">
          <div
            className={cn(
              "flex h-12 w-12 items-center justify-center rounded-full",
              readinessData?.ready ? "bg-green-500/10" : "bg-primary/10"
            )}
          >
            {readinessData?.ready ? (
              <CheckCircle2 className="h-6 w-6 text-green-500" />
            ) : (
              <Key className="h-6 w-6 text-primary" />
            )}
          </div>
          <div className="flex-1">
            <p className="font-medium">
              {readinessData?.ready
                ? "Ready to Generate Videos!"
                : "Complete Your Setup"}
            </p>
            <p className="text-sm text-muted-foreground">
              {readinessData?.ready
                ? "All required integrations are configured."
                : missingCategories.length > 0
                ? `Configure integrations for: ${missingCategories
                    .map((c) => categoryNames[c] || c)
                    .join(", ")}`
                : "Add integrations to get started."}
            </p>
            <Progress value={Math.min(readinessProgress, 100)} className="mt-2 h-2" />
          </div>
        </CardContent>
      </Card>

      {/* Category Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="all">
            All ({integrations.length})
          </TabsTrigger>
          {categoryKeys.map((catKey) => {
            const count = integrations.filter((i) => i.category === catKey).length
            return (
              <TabsTrigger key={catKey} value={catKey}>
                {categoryIcons[catKey] || "🔧"} {categoriesDict[catKey] || catKey} ({count})
              </TabsTrigger>
            )
          })}
        </TabsList>

        <TabsContent value={activeTab} className="mt-6">
          {filteredIntegrations.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Key className="h-12 w-12 text-muted-foreground" />
                <h3 className="mt-4 text-lg font-medium">No integrations</h3>
                <p className="text-sm text-muted-foreground">
                  Add your first integration to get started.
                </p>
                <Button className="mt-4" onClick={() => setAddDialogOpen(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Integration
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {filteredIntegrations.map((integration) => (
                <IntegrationCard
                  key={integration.id}
                  integration={integration}
                  onDelete={() => deleteMutation.mutate(integration.id)}
                  onValidate={() => validateMutation.mutate(integration.id)}
                  onToggle={(active) =>
                    toggleMutation.mutate({ id: integration.id, isActive: active })
                  }
                  isValidating={validateMutation.isPending}
                />
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Add Dialog */}
      <AddIntegrationDialog
        open={addDialogOpen}
        onOpenChange={setAddDialogOpen}
        availableIntegrations={availableIntegrations}
        existingProviders={existingProviders}
      />
    </div>
  )
}
