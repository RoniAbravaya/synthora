/**
 * Settings Page
 * 
 * User settings, subscription management, and preferences.
 */

import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  User,
  CreditCard,
  Bell,
  Palette,
  Shield,
  Loader2,
  Check,
  Crown,
  Sparkles,
  ExternalLink,
  Calendar,
  AlertCircle,
  Video,
  DollarSign,
  Info,
} from "lucide-react"
import { cn, formatDate, formatCurrency } from "@/lib/utils"
import { useAuth } from "@/contexts/AuthContext"
import { useTheme } from "@/contexts/ThemeContext"
import {
  usePlans,
  useSubscriptionStatus,
  useCreateCheckout,
  useCreatePortal,
  useCancelSubscription,
  useReactivateSubscription,
} from "@/hooks/useSubscription"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Switch } from "@/components/ui/switch"
import { Separator } from "@/components/ui/separator"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import type { SubscriptionPlan } from "@/types"
import {
  generationSettingsService,
  type UserGenerationSettings,
  type UserGenerationSettingsUpdate,
  type AvailableProvidersResponse,
  type CostEstimateResponse,
} from "@/services/generationSettings"

// =============================================================================
// Profile Tab
// =============================================================================

function ProfileTab() {
  const { user } = useAuth()

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Profile Information</CardTitle>
          <CardDescription>
            Your account details from Google Sign-In
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center gap-4">
            <Avatar className="h-20 w-20">
              <AvatarImage src={user?.photo_url || undefined} />
              <AvatarFallback className="text-2xl">
                {user?.display_name?.[0] || user?.email?.[0] || "U"}
              </AvatarFallback>
            </Avatar>
            <div>
              <h3 className="text-lg font-medium">{user?.display_name}</h3>
              <p className="text-sm text-muted-foreground">{user?.email}</p>
              <div className="mt-2 flex items-center gap-2">
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 text-xs font-medium",
                    user?.role === "admin"
                      ? "bg-purple-500/10 text-purple-500"
                      : user?.role === "premium"
                      ? "bg-gradient-synthora text-white"
                      : "bg-muted text-muted-foreground"
                  )}
                >
                  {user?.role === "admin" ? "Admin" : user?.role === "premium" ? "Premium" : "Free"}
                </span>
              </div>
            </div>
          </div>

          <Separator />

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>Display Name</Label>
              <Input value={user?.display_name || ""} disabled />
              <p className="text-xs text-muted-foreground">
                Managed by Google Sign-In
              </p>
            </div>
            <div className="space-y-2">
              <Label>Email</Label>
              <Input value={user?.email || ""} disabled />
              <p className="text-xs text-muted-foreground">
                Managed by Google Sign-In
              </p>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Member Since</Label>
            <p className="text-sm">
              {user?.created_at ? formatDate(user.created_at) : "Unknown"}
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// =============================================================================
// Subscription Tab
// =============================================================================

function SubscriptionTab() {
  const { user } = useAuth()
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false)

  const { data: plansData, isLoading: plansLoading } = usePlans()
  const { data: statusData, isLoading: statusLoading } = useSubscriptionStatus()
  
  const checkoutMutation = useCreateCheckout()
  const portalMutation = useCreatePortal()
  const cancelMutation = useCancelSubscription()
  const reactivateMutation = useReactivateSubscription()

  const plans = plansData?.plans || []
  const subscription = statusData?.subscription
  const isPremium = statusData?.is_premium || user?.role === "premium" || user?.role === "admin"

  const handleUpgrade = (plan: SubscriptionPlan) => {
    checkoutMutation.mutate(plan)
  }

  const handleManageBilling = () => {
    portalMutation.mutate()
  }

  const handleCancel = async () => {
    await cancelMutation.mutateAsync()
    setCancelDialogOpen(false)
  }

  const handleReactivate = () => {
    reactivateMutation.mutate()
  }

  if (plansLoading || statusLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Current Plan */}
      <Card className={cn(isPremium && "border-primary/50")}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                {isPremium ? (
                  <>
                    <Crown className="h-5 w-5 text-primary" />
                    Premium Plan
                  </>
                ) : (
                  <>
                    <User className="h-5 w-5" />
                    Free Plan
                  </>
                )}
              </CardTitle>
              <CardDescription>
                {isPremium
                  ? "You have access to all premium features"
                  : "Upgrade to unlock unlimited videos and AI suggestions"}
              </CardDescription>
            </div>
            {isPremium && subscription && (
              <Button variant="outline" onClick={handleManageBilling}>
                <ExternalLink className="mr-2 h-4 w-4" />
                Manage Billing
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {isPremium && subscription ? (
            <div className="space-y-4">
              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <p className="text-sm text-muted-foreground">Plan</p>
                  <p className="font-medium capitalize">{subscription.plan}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Status</p>
                  <p className="flex items-center gap-1 font-medium">
                    {subscription.status === "active" ? (
                      <>
                        <Check className="h-4 w-4 text-green-500" />
                        Active
                      </>
                    ) : (
                      <>
                        <AlertCircle className="h-4 w-4 text-yellow-500" />
                        {subscription.status}
                      </>
                    )}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">
                    {subscription.cancel_at_period_end ? "Cancels on" : "Renews on"}
                  </p>
                  <p className="font-medium">
                    {formatDate(subscription.current_period_end)}
                  </p>
                </div>
              </div>

              {subscription.cancel_at_period_end ? (
                <div className="rounded-lg border border-yellow-500/50 bg-yellow-500/10 p-4">
                  <p className="text-sm">
                    Your subscription will be canceled on{" "}
                    {formatDate(subscription.current_period_end)}. You'll still have access
                    until then.
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-2"
                    onClick={handleReactivate}
                    disabled={reactivateMutation.isPending}
                  >
                    {reactivateMutation.isPending && (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    )}
                    Reactivate Subscription
                  </Button>
                </div>
              ) : (
                <Button
                  variant="outline"
                  className="text-destructive hover:text-destructive"
                  onClick={() => setCancelDialogOpen(true)}
                >
                  Cancel Subscription
                </Button>
              )}
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm">
                <Check className="h-4 w-4 text-muted-foreground" />
                <span>1 video per day</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Check className="h-4 w-4 text-muted-foreground" />
                <span>Basic templates</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span className="ml-6">No AI suggestions</span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Upgrade Plans (for free users) */}
      {!isPremium && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Upgrade to Premium</h3>
          <div className="grid gap-4 md:grid-cols-2">
            {plans.map((plan) => (
              <Card
                key={plan.id}
                className={cn(
                  "relative cursor-pointer transition-all hover:border-primary/50",
                  plan.id === "annual" && "border-primary"
                )}
              >
                {plan.id === "annual" && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-gradient-synthora px-3 py-1 text-xs font-medium text-white">
                    Best Value
                  </div>
                )}
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>{plan.name}</span>
                    <span className="text-2xl font-bold">
                      {formatCurrency(plan.price)}
                      <span className="text-sm font-normal text-muted-foreground">
                        /{plan.interval}
                      </span>
                    </span>
                  </CardTitle>
                  {plan.id === "annual" && (
                    <CardDescription className="text-green-500">
                      Save $10/year compared to monthly
                    </CardDescription>
                  )}
                </CardHeader>
                <CardContent className="space-y-4">
                  <ul className="space-y-2">
                    {plan.features.map((feature, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm">
                        <Check className="h-4 w-4 text-primary" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                  <Button
                    className="w-full"
                    variant={plan.id === "annual" ? "default" : "outline"}
                    onClick={() => handleUpgrade(plan.id as SubscriptionPlan)}
                    disabled={checkoutMutation.isPending}
                  >
                    {checkoutMutation.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Sparkles className="mr-2 h-4 w-4" />
                    )}
                    Upgrade Now
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Cancel Dialog */}
      <Dialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancel Subscription</DialogTitle>
            <DialogDescription>
              Are you sure you want to cancel your subscription? You'll lose access to:
            </DialogDescription>
          </DialogHeader>
          <ul className="space-y-2 py-4">
            <li className="flex items-center gap-2 text-sm">
              <AlertCircle className="h-4 w-4 text-destructive" />
              Unlimited video generation
            </li>
            <li className="flex items-center gap-2 text-sm">
              <AlertCircle className="h-4 w-4 text-destructive" />
              AI-powered suggestions
            </li>
            <li className="flex items-center gap-2 text-sm">
              <AlertCircle className="h-4 w-4 text-destructive" />
              Indefinite video storage
            </li>
          </ul>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCancelDialogOpen(false)}>
              Keep Subscription
            </Button>
            <Button
              variant="destructive"
              onClick={handleCancel}
              disabled={cancelMutation.isPending}
            >
              {cancelMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Cancel Subscription
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// =============================================================================
// Appearance Tab
// =============================================================================

function AppearanceTab() {
  const { theme, setTheme } = useTheme()

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Theme</CardTitle>
          <CardDescription>
            Choose your preferred color theme
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <button
              className={cn(
                "flex flex-col items-center gap-2 rounded-lg border p-4 transition-all hover:border-primary",
                theme === "dark" && "border-primary bg-primary/5"
              )}
              onClick={() => setTheme("dark")}
            >
              <div className="h-20 w-full rounded bg-slate-900" />
              <span className="text-sm font-medium">Dark</span>
              {theme === "dark" && <Check className="h-4 w-4 text-primary" />}
            </button>
            <button
              className={cn(
                "flex flex-col items-center gap-2 rounded-lg border p-4 transition-all hover:border-primary",
                theme === "light" && "border-primary bg-primary/5"
              )}
              onClick={() => setTheme("light")}
            >
              <div className="h-20 w-full rounded bg-slate-100" />
              <span className="text-sm font-medium">Light</span>
              {theme === "light" && <Check className="h-4 w-4 text-primary" />}
            </button>
            <button
              className={cn(
                "flex flex-col items-center gap-2 rounded-lg border p-4 transition-all hover:border-primary",
                theme === "system" && "border-primary bg-primary/5"
              )}
              onClick={() => setTheme("system")}
            >
              <div className="flex h-20 w-full overflow-hidden rounded">
                <div className="w-1/2 bg-slate-100" />
                <div className="w-1/2 bg-slate-900" />
              </div>
              <span className="text-sm font-medium">System</span>
              {theme === "system" && <Check className="h-4 w-4 text-primary" />}
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// =============================================================================
// Notifications Tab
// =============================================================================

function NotificationsTab() {
  const [emailNotifications, setEmailNotifications] = useState(true)
  const [videoComplete, setVideoComplete] = useState(true)
  const [postPublished, setPostPublished] = useState(true)
  const [suggestions, setSuggestions] = useState(true)

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Notification Preferences</CardTitle>
          <CardDescription>
            Choose what notifications you want to receive
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Email Notifications</p>
              <p className="text-sm text-muted-foreground">
                Receive notifications via email
              </p>
            </div>
            <Switch checked={emailNotifications} onCheckedChange={setEmailNotifications} />
          </div>

          <Separator />

          <div className="space-y-4">
            <h4 className="text-sm font-medium">In-App Notifications</h4>
            
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm">Video Generation Complete</p>
                <p className="text-xs text-muted-foreground">
                  When your video finishes generating
                </p>
              </div>
              <Switch checked={videoComplete} onCheckedChange={setVideoComplete} />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm">Post Published</p>
                <p className="text-xs text-muted-foreground">
                  When your post is published to social media
                </p>
              </div>
              <Switch checked={postPublished} onCheckedChange={setPostPublished} />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm">AI Suggestions</p>
                <p className="text-xs text-muted-foreground">
                  New recommendations from AI (Premium only)
                </p>
              </div>
              <Switch checked={suggestions} onCheckedChange={setSuggestions} />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// =============================================================================
// Video Generation Tab
// =============================================================================

function VideoGenerationTab() {
  const queryClient = useQueryClient()
  
  // Queries
  const { data: settings, isLoading: settingsLoading } = useQuery({
    queryKey: ["generationSettings"],
    queryFn: generationSettingsService.get,
  })
  
  const { data: availableProviders, isLoading: providersLoading } = useQuery({
    queryKey: ["availableProviders"],
    queryFn: generationSettingsService.getAvailableProviders,
  })
  
  const { data: costEstimate, isLoading: costLoading } = useQuery({
    queryKey: ["costEstimate"],
    queryFn: generationSettingsService.getCostEstimate,
  })
  
  // Mutation
  const updateMutation = useMutation({
    mutationFn: (updates: UserGenerationSettingsUpdate) =>
      generationSettingsService.update(updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["generationSettings"] })
      queryClient.invalidateQueries({ queryKey: ["costEstimate"] })
    },
  })
  
  const handleProviderChange = (category: string, value: string) => {
    const key = `default_${category}_provider` as keyof UserGenerationSettingsUpdate
    updateMutation.mutate({ [key]: value === "auto" ? null : value })
  }
  
  const handleSubtitleStyleChange = (value: string) => {
    updateMutation.mutate({ subtitle_style: value })
  }
  
  if (settingsLoading || providersLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }
  
  const categories = [
    { key: "script", label: "Script Generation", description: "AI model for generating video scripts" },
    { key: "voice", label: "Voice Generation", description: "Text-to-speech provider" },
    { key: "media", label: "Stock Media", description: "Source for stock videos and images" },
    { key: "video_ai", label: "AI Video Generation", description: "AI-generated video clips (optional)" },
    { key: "assembly", label: "Video Assembly", description: "Video processing engine" },
  ]
  
  const getProvidersForCategory = (category: string) => {
    if (!availableProviders) return []
    return availableProviders.providers[category as keyof typeof availableProviders.providers] || []
  }
  
  const getCurrentValue = (category: string) => {
    if (!settings) return "auto"
    const key = `default_${category}_provider` as keyof UserGenerationSettings
    return settings[key] || "auto"
  }

  return (
    <div className="space-y-6">
      {/* Provider Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Video className="h-5 w-5" />
            Default Providers
          </CardTitle>
          <CardDescription>
            Choose default AI providers for each step of video generation.
            If not set, the first available provider will be used.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {categories.map((cat) => {
            const providers = getProvidersForCategory(cat.key)
            const currentValue = getCurrentValue(cat.key)
            
            return (
              <div key={cat.key} className="space-y-2">
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-sm font-medium">{cat.label}</Label>
                    <p className="text-xs text-muted-foreground">{cat.description}</p>
                  </div>
                  <Select
                    value={currentValue}
                    onValueChange={(v) => handleProviderChange(cat.key, v)}
                    disabled={updateMutation.isPending || providers.length === 0}
                  >
                    <SelectTrigger className="w-[200px]">
                      <SelectValue placeholder="Select provider" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="auto">
                        <span className="flex items-center gap-2">
                          <Sparkles className="h-4 w-4" />
                          Auto (First Available)
                        </span>
                      </SelectItem>
                      {providers.map((p) => (
                        <SelectItem
                          key={p.provider}
                          value={p.provider}
                          disabled={!p.is_valid}
                        >
                          <span className="flex items-center gap-2">
                            {p.display_name}
                            {!p.is_valid && (
                              <span className="text-xs text-muted-foreground">(Not configured)</span>
                            )}
                            {p.estimated_cost > 0 && (
                              <span className="text-xs text-muted-foreground">
                                ~${p.estimated_cost.toFixed(3)}
                              </span>
                            )}
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                {providers.length === 0 && (
                  <p className="text-xs text-amber-500">
                    No providers configured. Set up integrations first.
                  </p>
                )}
              </div>
            )
          })}
        </CardContent>
      </Card>

      {/* Subtitle Style */}
      <Card>
        <CardHeader>
          <CardTitle>Subtitle Style</CardTitle>
          <CardDescription>
            Choose how subtitles appear on your videos
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            {availableProviders?.subtitle_styles.map((style) => (
              <button
                key={style.name}
                className={cn(
                  "flex flex-col items-center gap-2 rounded-lg border p-4 transition-all hover:border-primary",
                  settings?.subtitle_style === style.name && "border-primary bg-primary/5"
                )}
                onClick={() => handleSubtitleStyleChange(style.name)}
                disabled={updateMutation.isPending}
              >
                <div
                  className={cn(
                    "flex h-12 w-full items-center justify-center rounded text-sm font-medium",
                    style.name === "classic" && "bg-black text-white",
                    style.name === "modern" && "bg-black/80 text-white rounded-sm",
                    style.name === "bold" && "bg-yellow-400 text-black font-bold",
                    style.name === "minimal" && "text-white drop-shadow-lg"
                  )}
                  style={style.name === "minimal" ? { textShadow: "2px 2px 4px black" } : undefined}
                >
                  Sample Text
                </div>
                <span className="text-sm font-medium">{style.display_name}</span>
                <span className="text-xs text-muted-foreground text-center">{style.description}</span>
                {settings?.subtitle_style === style.name && (
                  <Check className="h-4 w-4 text-primary" />
                )}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Cost Estimate */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            Estimated Cost per Video
          </CardTitle>
          <CardDescription>
            Based on your selected providers (actual cost may vary)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {costLoading ? (
            <Loader2 className="h-6 w-6 animate-spin" />
          ) : costEstimate ? (
            <div className="space-y-4">
              <div className="grid gap-2">
                {costEstimate.breakdown.map((item, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span className="capitalize">{item.category}</span>
                      <span className="text-muted-foreground">
                        ({item.provider_name})
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono">${item.cost.toFixed(4)}</span>
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger>
                            <Info className="h-3 w-3 text-muted-foreground" />
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>{item.description}</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </div>
                  </div>
                ))}
              </div>
              <Separator />
              <div className="flex items-center justify-between font-medium">
                <span>Total Estimated Cost</span>
                <span className="text-lg font-mono text-primary">
                  ${costEstimate.total_cost.toFixed(2)} {costEstimate.currency}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                {costEstimate.assumptions}
              </p>
            </div>
          ) : (
            <p className="text-muted-foreground">Unable to calculate cost estimate</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

// =============================================================================
// Main Page Component
// =============================================================================

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Manage your account and preferences
        </p>
      </div>

      <Tabs defaultValue="profile" className="space-y-6">
        <TabsList className="flex-wrap">
          <TabsTrigger value="profile" className="gap-2">
            <User className="h-4 w-4" />
            Profile
          </TabsTrigger>
          <TabsTrigger value="subscription" className="gap-2">
            <CreditCard className="h-4 w-4" />
            Subscription
          </TabsTrigger>
          <TabsTrigger value="video-generation" className="gap-2">
            <Video className="h-4 w-4" />
            Video Generation
          </TabsTrigger>
          <TabsTrigger value="appearance" className="gap-2">
            <Palette className="h-4 w-4" />
            Appearance
          </TabsTrigger>
          <TabsTrigger value="notifications" className="gap-2">
            <Bell className="h-4 w-4" />
            Notifications
          </TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <ProfileTab />
        </TabsContent>

        <TabsContent value="subscription">
          <SubscriptionTab />
        </TabsContent>

        <TabsContent value="video-generation">
          <VideoGenerationTab />
        </TabsContent>

        <TabsContent value="appearance">
          <AppearanceTab />
        </TabsContent>

        <TabsContent value="notifications">
          <NotificationsTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
