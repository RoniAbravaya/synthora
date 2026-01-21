/**
 * Settings Page
 * 
 * User settings, subscription management, and preferences.
 */

import { useState } from "react"
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
import type { SubscriptionPlan } from "@/types"

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
        <TabsList>
          <TabsTrigger value="profile" className="gap-2">
            <User className="h-4 w-4" />
            Profile
          </TabsTrigger>
          <TabsTrigger value="subscription" className="gap-2">
            <CreditCard className="h-4 w-4" />
            Subscription
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
