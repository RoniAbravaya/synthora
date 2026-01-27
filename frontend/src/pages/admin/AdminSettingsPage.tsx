/**
 * Admin Settings Page
 * 
 * System settings, feature flags, and configuration management.
 */

import { useState, useEffect } from "react"
import {
  Settings,
  ToggleLeft,
  Gauge,
  Database,
  Plus,
  Trash2,
  Save,
  Loader2,
  RefreshCw,
  AlertCircle,
  Check,
  Edit2,
  X,
} from "lucide-react"
import { cn } from "@/lib/utils"
import {
  useAdminSettings,
  useSetSetting,
  useDeleteSetting,
} from "@/hooks/useAdmin"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Switch } from "@/components/ui/switch"
import { Separator } from "@/components/ui/separator"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

// =============================================================================
// Types
// =============================================================================

interface FeatureFlag {
  key: string
  label: string
  description: string
  defaultValue: boolean
}

interface SystemLimit {
  key: string
  label: string
  description: string
  unit: string
  defaultValue: number
  min: number
  max: number
}

// =============================================================================
// Default Feature Flags
// =============================================================================

const DEFAULT_FEATURE_FLAGS: FeatureFlag[] = [
  {
    key: "feature.ai_suggestions",
    label: "AI Suggestions",
    description: "Enable AI-powered content suggestions for premium users",
    defaultValue: true,
  },
  {
    key: "feature.scheduling",
    label: "Post Scheduling",
    description: "Allow users to schedule posts for future publishing",
    defaultValue: true,
  },
  {
    key: "feature.analytics",
    label: "Analytics Dashboard",
    description: "Enable the analytics dashboard for all users",
    defaultValue: true,
  },
  {
    key: "feature.video_generation",
    label: "Video Generation",
    description: "Enable the video generation feature",
    defaultValue: true,
  },
  {
    key: "feature.social_posting",
    label: "Social Media Posting",
    description: "Allow posting to connected social media accounts",
    defaultValue: true,
  },
  {
    key: "feature.user_registration",
    label: "User Registration",
    description: "Allow new users to sign up (disable for maintenance)",
    defaultValue: true,
  },
]

// =============================================================================
// Default System Limits
// =============================================================================

const DEFAULT_SYSTEM_LIMITS: SystemLimit[] = [
  {
    key: "limit.free_videos_per_day",
    label: "Free Videos Per Day",
    description: "Maximum videos a free user can generate daily",
    unit: "videos",
    defaultValue: 1,
    min: 0,
    max: 10,
  },
  {
    key: "limit.free_retention_days",
    label: "Free Video Retention",
    description: "Days to keep videos for free users",
    unit: "days",
    defaultValue: 30,
    min: 1,
    max: 365,
  },
  {
    key: "limit.rate_limit_per_minute",
    label: "API Rate Limit",
    description: "Maximum API requests per minute per user",
    unit: "requests",
    defaultValue: 100,
    min: 10,
    max: 1000,
  },
  {
    key: "limit.max_video_duration",
    label: "Max Video Duration",
    description: "Maximum video duration in seconds",
    unit: "seconds",
    defaultValue: 300,
    min: 30,
    max: 600,
  },
  {
    key: "limit.max_concurrent_jobs",
    label: "Max Concurrent Jobs",
    description: "Maximum concurrent video generation jobs per user",
    unit: "jobs",
    defaultValue: 1,
    min: 1,
    max: 5,
  },
]

// =============================================================================
// Feature Flags Tab
// =============================================================================

interface FeatureFlagsTabProps {
  settings: Record<string, unknown>
}

function FeatureFlagsTab({ settings }: FeatureFlagsTabProps) {
  const setSettingMutation = useSetSetting()
  const [pendingChanges, setPendingChanges] = useState<Record<string, boolean>>({})
  const [saving, setSaving] = useState<string | null>(null)

  const handleToggle = async (key: string, value: boolean) => {
    setSaving(key)
    try {
      await setSettingMutation.mutateAsync({
        key,
        value,
        description: DEFAULT_FEATURE_FLAGS.find(f => f.key === key)?.description,
      })
    } finally {
      setSaving(null)
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ToggleLeft className="h-5 w-5" />
            Feature Flags
          </CardTitle>
          <CardDescription>
            Enable or disable features across the platform
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {DEFAULT_FEATURE_FLAGS.map((flag) => {
            const currentValue = settings[flag.key] !== undefined
              ? Boolean(settings[flag.key])
              : flag.defaultValue
            const isSaving = saving === flag.key

            return (
              <div
                key={flag.key}
                className="flex items-center justify-between gap-4 rounded-lg border p-4"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Label className="text-base font-medium">{flag.label}</Label>
                    {isSaving && (
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {flag.description}
                  </p>
                  <p className="text-xs text-muted-foreground font-mono">
                    {flag.key}
                  </p>
                </div>
                <Switch
                  checked={currentValue}
                  onCheckedChange={(checked) => handleToggle(flag.key, checked)}
                  disabled={isSaving}
                />
              </div>
            )
          })}
        </CardContent>
      </Card>
    </div>
  )
}

// =============================================================================
// System Limits Tab
// =============================================================================

interface SystemLimitsTabProps {
  settings: Record<string, unknown>
}

function SystemLimitsTab({ settings }: SystemLimitsTabProps) {
  const setSettingMutation = useSetSetting()
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [editValue, setEditValue] = useState<number>(0)
  const [saving, setSaving] = useState(false)

  const handleEdit = (limit: SystemLimit) => {
    const currentValue = settings[limit.key] !== undefined
      ? Number(settings[limit.key])
      : limit.defaultValue
    setEditingKey(limit.key)
    setEditValue(currentValue)
  }

  const handleSave = async (limit: SystemLimit) => {
    setSaving(true)
    try {
      await setSettingMutation.mutateAsync({
        key: limit.key,
        value: editValue,
        description: limit.description,
      })
      setEditingKey(null)
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    setEditingKey(null)
    setEditValue(0)
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Gauge className="h-5 w-5" />
            System Limits
          </CardTitle>
          <CardDescription>
            Configure resource limits and quotas
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {DEFAULT_SYSTEM_LIMITS.map((limit) => {
            const currentValue = settings[limit.key] !== undefined
              ? Number(settings[limit.key])
              : limit.defaultValue
            const isEditing = editingKey === limit.key

            return (
              <div
                key={limit.key}
                className="flex items-center justify-between gap-4 rounded-lg border p-4"
              >
                <div className="flex-1 space-y-1">
                  <Label className="text-base font-medium">{limit.label}</Label>
                  <p className="text-sm text-muted-foreground">
                    {limit.description}
                  </p>
                  <p className="text-xs text-muted-foreground font-mono">
                    {limit.key}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {isEditing ? (
                    <>
                      <Input
                        type="number"
                        value={editValue}
                        onChange={(e) => setEditValue(Number(e.target.value))}
                        min={limit.min}
                        max={limit.max}
                        className="w-24"
                      />
                      <span className="text-sm text-muted-foreground">
                        {limit.unit}
                      </span>
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => handleSave(limit)}
                        disabled={saving}
                      >
                        {saving ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Check className="h-4 w-4 text-green-500" />
                        )}
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={handleCancel}
                        disabled={saving}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </>
                  ) : (
                    <>
                      <span className="font-mono text-lg font-medium">
                        {currentValue}
                      </span>
                      <span className="text-sm text-muted-foreground">
                        {limit.unit}
                      </span>
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => handleEdit(limit)}
                      >
                        <Edit2 className="h-4 w-4" />
                      </Button>
                    </>
                  )}
                </div>
              </div>
            )
          })}
        </CardContent>
      </Card>
    </div>
  )
}

// =============================================================================
// Custom Settings Tab
// =============================================================================

interface CustomSettingsTabProps {
  settings: Record<string, unknown>
}

function CustomSettingsTab({ settings }: CustomSettingsTabProps) {
  const setSettingMutation = useSetSetting()
  const deleteSettingMutation = useDeleteSetting()
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [newSetting, setNewSetting] = useState({
    key: "",
    value: "",
    valueType: "string" as "string" | "number" | "boolean" | "json",
    description: "",
  })

  // Filter out known feature flags and limits
  const knownKeys = [
    ...DEFAULT_FEATURE_FLAGS.map(f => f.key),
    ...DEFAULT_SYSTEM_LIMITS.map(l => l.key),
  ]
  const customSettings = Object.entries(settings).filter(
    ([key]) => !knownKeys.includes(key)
  )

  const handleAddSetting = async () => {
    let parsedValue: unknown = newSetting.value

    try {
      switch (newSetting.valueType) {
        case "number":
          parsedValue = Number(newSetting.value)
          break
        case "boolean":
          parsedValue = newSetting.value.toLowerCase() === "true"
          break
        case "json":
          parsedValue = JSON.parse(newSetting.value)
          break
      }
    } catch {
      // Keep as string if parsing fails
    }

    await setSettingMutation.mutateAsync({
      key: newSetting.key,
      value: parsedValue,
      description: newSetting.description || undefined,
    })

    setAddDialogOpen(false)
    setNewSetting({ key: "", value: "", valueType: "string", description: "" })
  }

  const handleDeleteSetting = async (key: string) => {
    await deleteSettingMutation.mutateAsync(key)
  }

  const formatValue = (value: unknown): string => {
    if (typeof value === "object") {
      return JSON.stringify(value, null, 2)
    }
    return String(value)
  }

  const getValueType = (value: unknown): string => {
    if (typeof value === "boolean") return "boolean"
    if (typeof value === "number") return "number"
    if (typeof value === "object") return "json"
    return "string"
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-5 w-5" />
                Custom Settings
              </CardTitle>
              <CardDescription>
                Manage custom key-value configuration settings
              </CardDescription>
            </div>
            <Button onClick={() => setAddDialogOpen(true)} className="gap-2">
              <Plus className="h-4 w-4" />
              Add Setting
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {customSettings.length === 0 ? (
            <div className="flex h-32 flex-col items-center justify-center text-muted-foreground">
              <Database className="mb-2 h-8 w-8" />
              <p>No custom settings configured</p>
              <p className="text-sm">Click "Add Setting" to create one</p>
            </div>
          ) : (
            <div className="space-y-4">
              {customSettings.map(([key, value]) => (
                <div
                  key={key}
                  className="flex items-start justify-between gap-4 rounded-lg border p-4"
                >
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center gap-2">
                      <Label className="font-mono text-sm">{key}</Label>
                      <span className={cn(
                        "rounded-full px-2 py-0.5 text-xs",
                        getValueType(value) === "boolean" && "bg-blue-500/10 text-blue-500",
                        getValueType(value) === "number" && "bg-green-500/10 text-green-500",
                        getValueType(value) === "json" && "bg-purple-500/10 text-purple-500",
                        getValueType(value) === "string" && "bg-muted text-muted-foreground"
                      )}>
                        {getValueType(value)}
                      </span>
                    </div>
                    <pre className="rounded bg-muted p-2 text-sm overflow-x-auto">
                      {formatValue(value)}
                    </pre>
                  </div>
                  <Button
                    size="icon"
                    variant="ghost"
                    onClick={() => handleDeleteSetting(key)}
                    disabled={deleteSettingMutation.isPending}
                  >
                    {deleteSettingMutation.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4 text-destructive" />
                    )}
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Add Setting Dialog */}
      <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Custom Setting</DialogTitle>
            <DialogDescription>
              Create a new configuration setting
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Key</Label>
              <Input
                placeholder="setting.key.name"
                value={newSetting.key}
                onChange={(e) => setNewSetting(s => ({ ...s, key: e.target.value }))}
              />
              <p className="text-xs text-muted-foreground">
                Use dot notation for organization (e.g., feature.new_feature)
              </p>
            </div>

            <div className="space-y-2">
              <Label>Value Type</Label>
              <Select
                value={newSetting.valueType}
                onValueChange={(v) => setNewSetting(s => ({
                  ...s,
                  valueType: v as typeof newSetting.valueType,
                }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="string">String</SelectItem>
                  <SelectItem value="number">Number</SelectItem>
                  <SelectItem value="boolean">Boolean</SelectItem>
                  <SelectItem value="json">JSON</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Value</Label>
              {newSetting.valueType === "json" ? (
                <Textarea
                  placeholder='{"key": "value"}'
                  value={newSetting.value}
                  onChange={(e) => setNewSetting(s => ({ ...s, value: e.target.value }))}
                  rows={4}
                  className="font-mono"
                />
              ) : newSetting.valueType === "boolean" ? (
                <Select
                  value={newSetting.value}
                  onValueChange={(v) => setNewSetting(s => ({ ...s, value: v }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select value" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="true">True</SelectItem>
                    <SelectItem value="false">False</SelectItem>
                  </SelectContent>
                </Select>
              ) : (
                <Input
                  type={newSetting.valueType === "number" ? "number" : "text"}
                  placeholder="Value"
                  value={newSetting.value}
                  onChange={(e) => setNewSetting(s => ({ ...s, value: e.target.value }))}
                />
              )}
            </div>

            <div className="space-y-2">
              <Label>Description (optional)</Label>
              <Input
                placeholder="What this setting does"
                value={newSetting.description}
                onChange={(e) => setNewSetting(s => ({ ...s, description: e.target.value }))}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setAddDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleAddSetting}
              disabled={!newSetting.key || !newSetting.value || setSettingMutation.isPending}
            >
              {setSettingMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Add Setting
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// =============================================================================
// Main Page Component
// =============================================================================

export default function AdminSettingsPage() {
  const { data, isLoading, refetch } = useAdminSettings()
  const settings = data?.settings || {}

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">System Settings</h1>
          <p className="text-muted-foreground">
            Configure platform-wide settings and feature flags
          </p>
        </div>
        <Button variant="outline" onClick={() => refetch()} className="gap-2">
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Warning Banner */}
      <Card className="border-yellow-500/50 bg-yellow-500/10">
        <CardContent className="flex items-start gap-3 p-4">
          <AlertCircle className="mt-0.5 h-5 w-5 text-yellow-500" />
          <div>
            <p className="font-medium text-yellow-500">Caution</p>
            <p className="text-sm text-muted-foreground">
              Changes to these settings affect all users immediately. Please be careful when modifying system limits or disabling features.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Settings Tabs */}
      <Tabs defaultValue="features" className="space-y-6">
        <TabsList>
          <TabsTrigger value="features" className="gap-2">
            <ToggleLeft className="h-4 w-4" />
            Feature Flags
          </TabsTrigger>
          <TabsTrigger value="limits" className="gap-2">
            <Gauge className="h-4 w-4" />
            System Limits
          </TabsTrigger>
          <TabsTrigger value="custom" className="gap-2">
            <Database className="h-4 w-4" />
            Custom Settings
          </TabsTrigger>
        </TabsList>

        <TabsContent value="features">
          <FeatureFlagsTab settings={settings} />
        </TabsContent>

        <TabsContent value="limits">
          <SystemLimitsTab settings={settings} />
        </TabsContent>

        <TabsContent value="custom">
          <CustomSettingsTab settings={settings} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
