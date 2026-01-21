/**
 * Dashboard Layout
 * 
 * Main layout for authenticated users with sidebar navigation.
 */

import { useState } from "react"
import { Outlet, NavLink, useLocation } from "react-router-dom"
import {
  LayoutDashboard,
  Video,
  FileText,
  Calendar,
  BarChart3,
  Settings,
  Plug,
  Share2,
  Lightbulb,
  Plus,
  Menu,
  X,
  Bell,
  ChevronDown,
  LogOut,
  User,
  CreditCard,
  Shield,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useAuth, useIsAdmin } from "@/contexts/AuthContext"
import { useUnreadCount } from "@/hooks/useNotifications"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

// =============================================================================
// Navigation Items
// =============================================================================

const mainNavItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/create", label: "Create Video", icon: Plus },
  { href: "/videos", label: "My Videos", icon: Video },
  { href: "/templates", label: "Templates", icon: FileText },
]

const publishNavItems = [
  { href: "/posts", label: "Posts", icon: Share2 },
  { href: "/calendar", label: "Calendar", icon: Calendar },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/suggestions", label: "AI Suggestions", icon: Lightbulb, premium: true },
]

const settingsNavItems = [
  { href: "/integrations", label: "Integrations", icon: Plug },
  { href: "/social-accounts", label: "Social Accounts", icon: Share2 },
  { href: "/settings", label: "Settings", icon: Settings },
]

const adminNavItems = [
  { href: "/admin", label: "Admin Dashboard", icon: Shield },
  { href: "/admin/users", label: "Manage Users", icon: User },
  { href: "/admin/settings", label: "System Settings", icon: Settings },
]

// =============================================================================
// Sidebar Component
// =============================================================================

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
}

function Sidebar({ isOpen, onClose }: SidebarProps) {
  const { user } = useAuth()
  const isAdmin = useIsAdmin()
  const location = useLocation()

  const NavItem = ({
    href,
    label,
    icon: Icon,
    premium,
  }: {
    href: string
    label: string
    icon: React.ComponentType<{ className?: string }>
    premium?: boolean
  }) => {
    const isActive = location.pathname === href

    return (
      <NavLink
        to={href}
        onClick={onClose}
        className={cn(
          "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
          isActive
            ? "bg-primary/10 text-primary"
            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        )}
      >
        <Icon className="h-4 w-4" />
        <span>{label}</span>
        {premium && user?.role === "free" && (
          <span className="ml-auto rounded bg-gradient-synthora px-1.5 py-0.5 text-[10px] font-semibold text-white">
            PRO
          </span>
        )}
      </NavLink>
    )
  }

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r bg-card transition-transform duration-300 lg:static lg:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Logo */}
        <div className="flex h-16 items-center gap-2 border-b px-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-synthora">
            <span className="text-lg font-bold text-white">S</span>
          </div>
          <span className="text-xl font-bold text-gradient">Synthora</span>
          <Button
            variant="ghost"
            size="icon"
            className="ml-auto lg:hidden"
            onClick={onClose}
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Navigation */}
        <ScrollArea className="flex-1 px-3 py-4">
          <div className="space-y-6">
            {/* Main */}
            <div className="space-y-1">
              <p className="px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Create
              </p>
              {mainNavItems.map((item) => (
                <NavItem key={item.href} {...item} />
              ))}
            </div>

            {/* Publish */}
            <div className="space-y-1">
              <p className="px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Publish
              </p>
              {publishNavItems.map((item) => (
                <NavItem key={item.href} {...item} />
              ))}
            </div>

            {/* Settings */}
            <div className="space-y-1">
              <p className="px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Settings
              </p>
              {settingsNavItems.map((item) => (
                <NavItem key={item.href} {...item} />
              ))}
            </div>

            {/* Admin */}
            {isAdmin && (
              <div className="space-y-1">
                <p className="px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Admin
                </p>
                {adminNavItems.map((item) => (
                  <NavItem key={item.href} {...item} />
                ))}
              </div>
            )}
          </div>
        </ScrollArea>

        {/* User tier badge */}
        <div className="border-t p-4">
          <div
            className={cn(
              "flex items-center justify-between rounded-lg p-3",
              user?.role === "premium" || user?.role === "admin"
                ? "bg-gradient-synthora text-white"
                : "bg-muted"
            )}
          >
            <div>
              <p className="text-sm font-medium">
                {user?.role === "admin"
                  ? "Admin"
                  : user?.role === "premium"
                  ? "Premium"
                  : "Free Plan"}
              </p>
              {user?.role === "free" && (
                <p className="text-xs opacity-80">1 video/day</p>
              )}
            </div>
            {user?.role === "free" && (
              <NavLink to="/settings">
                <Button size="sm" variant="secondary">
                  Upgrade
                </Button>
              </NavLink>
            )}
          </div>
        </div>
      </aside>
    </>
  )
}

// =============================================================================
// Header Component
// =============================================================================

interface HeaderProps {
  onMenuClick: () => void
}

function Header({ onMenuClick }: HeaderProps) {
  const { user, logout } = useAuth()
  const { data: unreadData } = useUnreadCount()
  const unreadCount = unreadData?.count ?? 0

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b bg-card/80 px-4 backdrop-blur-lg">
      {/* Mobile menu button */}
      <Button
        variant="ghost"
        size="icon"
        className="lg:hidden"
        onClick={onMenuClick}
      >
        <Menu className="h-5 w-5" />
      </Button>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Notifications */}
      <NavLink to="/dashboard">
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-destructive text-[10px] font-bold text-white">
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </Button>
      </NavLink>

      {/* User menu */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="flex items-center gap-2">
            <Avatar className="h-8 w-8">
              <AvatarImage src={user?.photo_url || undefined} />
              <AvatarFallback>
                {user?.display_name?.[0] || user?.email?.[0] || "U"}
              </AvatarFallback>
            </Avatar>
            <span className="hidden text-sm font-medium md:inline">
              {user?.display_name || user?.email}
            </span>
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuLabel>
            <div className="flex flex-col space-y-1">
              <p className="text-sm font-medium">{user?.display_name}</p>
              <p className="text-xs text-muted-foreground">{user?.email}</p>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem asChild>
            <NavLink to="/settings" className="flex items-center">
              <User className="mr-2 h-4 w-4" />
              Profile
            </NavLink>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <NavLink to="/settings" className="flex items-center">
              <CreditCard className="mr-2 h-4 w-4" />
              Subscription
            </NavLink>
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={logout} className="text-destructive">
            <LogOut className="mr-2 h-4 w-4" />
            Sign out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  )
}

// =============================================================================
// Layout Component
// =============================================================================

export default function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex flex-1 flex-col">
        <Header onMenuClick={() => setSidebarOpen(true)} />

        <main className="flex-1 overflow-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

