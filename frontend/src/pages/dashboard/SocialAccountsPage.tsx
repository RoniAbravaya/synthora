/**
 * Social Accounts Page
 * 
 * Connect and manage social media accounts.
 */

import { useState, useEffect } from "react"
import { useSearchParams } from "react-router-dom"
import {
  Youtube,
  Instagram,
  Facebook,
  Music2,
  Plus,
  Loader2,
  Check,
  AlertCircle,
  RefreshCw,
  Trash2,
  ExternalLink,
} from "lucide-react"
import { cn, formatRelativeTime } from "@/lib/utils"
import {
  useSocialAccounts,
  useConnectAccount,
  useDisconnectAccount,
  useRefreshToken,
} from "@/hooks/useSocialAccounts"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import toast from "react-hot-toast"
import type { SocialAccount, SocialPlatform } from "@/types"

// =============================================================================
// Platform Configuration
// =============================================================================

const platformConfig: Record<
  SocialPlatform,
  {
    name: string
    icon: typeof Youtube
    color: string
    bgColor: string
    description: string
  }
> = {
  youtube: {
    name: "YouTube",
    icon: Youtube,
    color: "text-red-500",
    bgColor: "bg-red-500/10",
    description: "Upload videos to your YouTube channel",
  },
  tiktok: {
    name: "TikTok",
    icon: Music2,
    color: "text-foreground",
    bgColor: "bg-foreground/10",
    description: "Post videos to your TikTok account",
  },
  instagram: {
    name: "Instagram",
    icon: Instagram,
    color: "text-pink-500",
    bgColor: "bg-pink-500/10",
    description: "Share Reels to your Instagram profile",
  },
  facebook: {
    name: "Facebook",
    icon: Facebook,
    color: "text-blue-600",
    bgColor: "bg-blue-600/10",
    description: "Post videos to your Facebook Page",
  },
}

const allPlatforms: SocialPlatform[] = ["youtube", "tiktok", "instagram", "facebook"]

// =============================================================================
// Connected Account Card
// =============================================================================

interface ConnectedAccountCardProps {
  account: SocialAccount
  onDisconnect: () => void
  onRefresh: () => void
  isRefreshing: boolean
}

function ConnectedAccountCard({
  account,
  onDisconnect,
  onRefresh,
  isRefreshing,
}: ConnectedAccountCardProps) {
  const config = platformConfig[account.platform]
  const Icon = config.icon
  const isExpired = account.token_expires_at && new Date(account.token_expires_at) < new Date()

  return (
    <Card className={cn(!account.is_active && "opacity-60")}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={cn("flex h-10 w-10 items-center justify-center rounded-lg", config.bgColor)}>
              <Icon className={cn("h-5 w-5", config.color)} />
            </div>
            <div>
              <CardTitle className="text-base">{config.name}</CardTitle>
              <CardDescription className="text-xs">
                @{account.platform_username || account.platform_user_id}
              </CardDescription>
            </div>
          </div>
          {account.is_active && !isExpired ? (
            <div className="flex items-center gap-1 text-sm text-green-500">
              <Check className="h-4 w-4" />
              Connected
            </div>
          ) : (
            <div className="flex items-center gap-1 text-sm text-yellow-500">
              <AlertCircle className="h-4 w-4" />
              {isExpired ? "Expired" : "Inactive"}
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Token Status */}
        {account.token_expires_at && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Token expires</span>
            <span className={isExpired ? "text-yellow-500" : ""}>
              {formatRelativeTime(account.token_expires_at)}
            </span>
          </div>
        )}

        {/* Connected since */}
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Connected</span>
          <span>{formatRelativeTime(account.created_at)}</span>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          {isExpired && (
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={onRefresh}
              disabled={isRefreshing}
            >
              {isRefreshing ? (
                <Loader2 className="mr-2 h-3 w-3 animate-spin" />
              ) : (
                <RefreshCw className="mr-2 h-3 w-3" />
              )}
              Reconnect
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={onDisconnect}
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
// Connect Platform Card
// =============================================================================

interface ConnectPlatformCardProps {
  platform: SocialPlatform
  onConnect: () => void
  isConnecting: boolean
}

function ConnectPlatformCard({ platform, onConnect, isConnecting }: ConnectPlatformCardProps) {
  const config = platformConfig[platform]
  const Icon = config.icon

  return (
    <Card className="border-dashed">
      <CardContent className="flex flex-col items-center justify-center py-8">
        <div className={cn("flex h-12 w-12 items-center justify-center rounded-lg", config.bgColor)}>
          <Icon className={cn("h-6 w-6", config.color)} />
        </div>
        <h3 className="mt-4 font-medium">{config.name}</h3>
        <p className="mt-1 text-center text-sm text-muted-foreground">
          {config.description}
        </p>
        <Button className="mt-4" onClick={onConnect} disabled={isConnecting}>
          {isConnecting ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Plus className="mr-2 h-4 w-4" />
          )}
          Connect
        </Button>
      </CardContent>
    </Card>
  )
}

// =============================================================================
// Main Page Component
// =============================================================================

export default function SocialAccountsPage() {
  const [disconnectId, setDisconnectId] = useState<string | null>(null)
  const [connectingPlatform, setConnectingPlatform] = useState<SocialPlatform | null>(null)
  const [searchParams, setSearchParams] = useSearchParams()

  const { data, isLoading, refetch } = useSocialAccounts()
  const connectMutation = useConnectAccount()
  const disconnectMutation = useDisconnectAccount()
  const refreshMutation = useRefreshToken()

  // Handle OAuth callback query parameters
  useEffect(() => {
    const success = searchParams.get("success")
    const error = searchParams.get("error")
    const platform = searchParams.get("platform")
    const account = searchParams.get("account")

    if (success === "true" && platform) {
      toast.success(`${platform.charAt(0).toUpperCase() + platform.slice(1)} account "${account || ''}" connected successfully!`)
      refetch() // Refresh the accounts list
      // Clear the query params
      setSearchParams({})
    } else if (error && platform) {
      const errorMessages: Record<string, string> = {
        token_exchange_failed: "Failed to complete authentication. Please try again.",
        channel_fetch_failed: "Could not fetch your channel information. Please try again.",
        no_channel: "No channel found for this account. Make sure you have a YouTube channel.",
        invalid_state: "Authentication session expired. Please try again.",
        user_not_found: "Session expired. Please log in again.",
        oauth_not_configured: "OAuth is not configured for this platform. Please contact support.",
        platform_not_implemented: "This platform is not yet supported.",
        server_error: "An unexpected error occurred. Please try again.",
        missing_params: "Invalid callback. Please try again.",
      }
      const message = errorMessages[error] || `Failed to connect ${platform}: ${error}`
      toast.error(message)
      // Clear the query params
      setSearchParams({})
    }
  }, [searchParams, setSearchParams, refetch])

  const accounts = data?.accounts || []
  const connectedPlatforms = accounts.map((a) => a.platform)
  const availablePlatforms = allPlatforms.filter((p) => !connectedPlatforms.includes(p))

  const handleConnect = async (platform: SocialPlatform) => {
    setConnectingPlatform(platform)
    try {
      await connectMutation.mutateAsync(platform)
    } catch {
      // Error already handled by mutation
    } finally {
      setConnectingPlatform(null)
    }
  }

  const handleDisconnect = async () => {
    if (!disconnectId) return
    await disconnectMutation.mutateAsync(disconnectId)
    setDisconnectId(null)
  }

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
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Social Accounts</h1>
        <p className="text-muted-foreground">
          Connect your social media accounts to publish videos
        </p>
      </div>

      {/* Connected Accounts */}
      {accounts.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Connected Accounts</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {accounts.map((account) => (
              <ConnectedAccountCard
                key={account.id}
                account={account}
                onDisconnect={() => setDisconnectId(account.id)}
                onRefresh={() => refreshMutation.mutate(account.id)}
                isRefreshing={refreshMutation.isPending}
              />
            ))}
          </div>
        </div>
      )}

      {/* Available Platforms */}
      {availablePlatforms.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">
            {accounts.length > 0 ? "Connect More Accounts" : "Connect Your Accounts"}
          </h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {availablePlatforms.map((platform) => (
              <ConnectPlatformCard
                key={platform}
                platform={platform}
                onConnect={() => handleConnect(platform)}
                isConnecting={connectingPlatform === platform}
              />
            ))}
          </div>
        </div>
      )}

      {/* All Connected State */}
      {availablePlatforms.length === 0 && accounts.length === allPlatforms.length && (
        <Card className="border-green-500/50 bg-green-500/5">
          <CardContent className="flex items-center gap-4 p-6">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-500/10">
              <Check className="h-6 w-6 text-green-500" />
            </div>
            <div>
              <h3 className="font-medium">All Platforms Connected</h3>
              <p className="text-sm text-muted-foreground">
                You've connected all available social media platforms.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Disconnect Confirmation */}
      <Dialog open={!!disconnectId} onOpenChange={() => setDisconnectId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Disconnect Account</DialogTitle>
            <DialogDescription>
              Are you sure you want to disconnect this account? You won't be able to post to
              this platform until you reconnect.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDisconnectId(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDisconnect}
              disabled={disconnectMutation.isPending}
            >
              {disconnectMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Disconnect
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
