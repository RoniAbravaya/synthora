/**
 * Admin Users Page
 * 
 * User management for admins - list, search, filter, and manage users.
 */

import { useState, useCallback } from "react"
import {
  Search,
  Filter,
  MoreHorizontal,
  User,
  Crown,
  Shield,
  Ban,
  CheckCircle,
  Loader2,
  ChevronLeft,
  ChevronRight,
  ArrowUpDown,
  Eye,
  UserCog,
  Trash2,
  Gift,
  XCircle,
  RefreshCw,
} from "lucide-react"
import { cn, formatDate, formatRelativeTime, debounce } from "@/lib/utils"
import {
  useAdminUsers,
  useAdminUserDetails,
  useUpdateUserRole,
  useUpdateUserStatus,
  useDeleteUser,
  useGrantPremium,
  useRevokePremium,
  type UserListFilters,
} from "@/hooks/useAdmin"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Separator } from "@/components/ui/separator"
import type { UserRole } from "@/types"

// =============================================================================
// Types
// =============================================================================

interface UserItem {
  id: string
  email: string
  display_name: string | null
  role: UserRole
  is_active: boolean
  created_at: string
  last_login: string | null
}

// =============================================================================
// User Role Badge
// =============================================================================

function RoleBadge({ role }: { role: UserRole }) {
  const config = {
    admin: {
      icon: Shield,
      label: "Admin",
      className: "bg-purple-500/10 text-purple-500 border-purple-500/20",
    },
    premium: {
      icon: Crown,
      label: "Premium",
      className: "bg-primary/10 text-primary border-primary/20",
    },
    free: {
      icon: User,
      label: "Free",
      className: "bg-muted text-muted-foreground border-border",
    },
  }[role]

  const Icon = config.icon

  return (
    <span className={cn(
      "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
      config.className
    )}>
      <Icon className="h-3 w-3" />
      {config.label}
    </span>
  )
}

// =============================================================================
// Status Badge
// =============================================================================

function StatusBadge({ isActive }: { isActive: boolean }) {
  return (
    <span className={cn(
      "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
      isActive
        ? "bg-green-500/10 text-green-500"
        : "bg-red-500/10 text-red-500"
    )}>
      {isActive ? (
        <>
          <CheckCircle className="h-3 w-3" />
          Active
        </>
      ) : (
        <>
          <Ban className="h-3 w-3" />
          Disabled
        </>
      )}
    </span>
  )
}

// =============================================================================
// User Details Dialog
// =============================================================================

interface UserDetailsDialogProps {
  userId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

function UserDetailsDialog({ userId, open, onOpenChange }: UserDetailsDialogProps) {
  const { data: user, isLoading } = useAdminUserDetails(userId)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>User Details</DialogTitle>
          <DialogDescription>
            Detailed information about this user
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="flex h-48 items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : user ? (
          <div className="space-y-6">
            {/* User Header */}
            <div className="flex items-center gap-4">
              <Avatar className="h-16 w-16">
                <AvatarImage src={user.photo_url || undefined} />
                <AvatarFallback className="text-xl">
                  {user.display_name?.[0] || user.email[0].toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <div>
                <h3 className="text-lg font-medium">
                  {user.display_name || "No name"}
                </h3>
                <p className="text-sm text-muted-foreground">{user.email}</p>
                <div className="mt-2 flex items-center gap-2">
                  <RoleBadge role={user.role} />
                  <StatusBadge isActive={user.is_active} />
                </div>
              </div>
            </div>

            <Separator />

            {/* User Info Grid */}
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <Label className="text-muted-foreground">User ID</Label>
                <p className="text-sm font-mono">{user.id}</p>
              </div>
              <div>
                <Label className="text-muted-foreground">Created At</Label>
                <p className="text-sm">{formatDate(user.created_at)}</p>
              </div>
              <div>
                <Label className="text-muted-foreground">Last Login</Label>
                <p className="text-sm">
                  {user.last_login ? formatRelativeTime(user.last_login) : "Never"}
                </p>
              </div>
              <div>
                <Label className="text-muted-foreground">Updated At</Label>
                <p className="text-sm">
                  {user.updated_at ? formatDate(user.updated_at) : "Never"}
                </p>
              </div>
            </div>

            <Separator />

            {/* Subscription Info */}
            <div>
              <h4 className="mb-2 font-medium">Subscription</h4>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <Label className="text-muted-foreground">Status</Label>
                  <p className="text-sm capitalize">
                    {user.subscription_status || "No subscription"}
                  </p>
                </div>
                <div>
                  <Label className="text-muted-foreground">Plan</Label>
                  <p className="text-sm capitalize">
                    {user.subscription_plan || "N/A"}
                  </p>
                </div>
              </div>
            </div>

            <Separator />

            {/* User Stats */}
            <div>
              <h4 className="mb-2 font-medium">Activity Stats</h4>
              <div className="grid grid-cols-4 gap-4">
                <div className="rounded-lg border p-3 text-center">
                  <p className="text-2xl font-bold">{user.stats.videos}</p>
                  <p className="text-xs text-muted-foreground">Videos</p>
                </div>
                <div className="rounded-lg border p-3 text-center">
                  <p className="text-2xl font-bold">{user.stats.posts}</p>
                  <p className="text-xs text-muted-foreground">Posts</p>
                </div>
                <div className="rounded-lg border p-3 text-center">
                  <p className="text-2xl font-bold">{user.stats.integrations}</p>
                  <p className="text-xs text-muted-foreground">Integrations</p>
                </div>
                <div className="rounded-lg border p-3 text-center">
                  <p className="text-2xl font-bold">{user.stats.social_accounts}</p>
                  <p className="text-xs text-muted-foreground">Social Accounts</p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex h-48 items-center justify-center text-muted-foreground">
            User not found
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

// =============================================================================
// Role Change Dialog
// =============================================================================

interface RoleChangeDialogProps {
  user: UserItem | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

function RoleChangeDialog({ user, open, onOpenChange }: RoleChangeDialogProps) {
  const [selectedRole, setSelectedRole] = useState<UserRole | "">("")
  const updateRoleMutation = useUpdateUserRole()

  const handleSubmit = async () => {
    if (!user || !selectedRole) return

    await updateRoleMutation.mutateAsync({
      userId: user.id,
      role: selectedRole,
    })
    onOpenChange(false)
    setSelectedRole("")
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Change User Role</DialogTitle>
          <DialogDescription>
            Change the role for {user?.display_name || user?.email}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>Current Role</Label>
            <div>
              {user && <RoleBadge role={user.role} />}
            </div>
          </div>

          <div className="space-y-2">
            <Label>New Role</Label>
            <Select value={selectedRole} onValueChange={(v) => setSelectedRole(v as UserRole)}>
              <SelectTrigger>
                <SelectValue placeholder="Select a role" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="free">
                  <span className="flex items-center gap-2">
                    <User className="h-4 w-4" />
                    Free
                  </span>
                </SelectItem>
                <SelectItem value="premium">
                  <span className="flex items-center gap-2">
                    <Crown className="h-4 w-4" />
                    Premium
                  </span>
                </SelectItem>
                <SelectItem value="admin">
                  <span className="flex items-center gap-2">
                    <Shield className="h-4 w-4" />
                    Admin
                  </span>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!selectedRole || selectedRole === user?.role || updateRoleMutation.isPending}
          >
            {updateRoleMutation.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            Change Role
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// =============================================================================
// Grant Premium Dialog
// =============================================================================

interface GrantPremiumDialogProps {
  user: UserItem | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

function GrantPremiumDialog({ user, open, onOpenChange }: GrantPremiumDialogProps) {
  const [months, setMonths] = useState("1")
  const grantPremiumMutation = useGrantPremium()

  const handleSubmit = async () => {
    if (!user) return

    await grantPremiumMutation.mutateAsync({
      userId: user.id,
      months: parseInt(months),
    })
    onOpenChange(false)
    setMonths("1")
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Grant Premium Access</DialogTitle>
          <DialogDescription>
            Grant premium access to {user?.display_name || user?.email}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>Duration (months)</Label>
            <Select value={months} onValueChange={setMonths}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1">1 month</SelectItem>
                <SelectItem value="3">3 months</SelectItem>
                <SelectItem value="6">6 months</SelectItem>
                <SelectItem value="12">12 months</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={grantPremiumMutation.isPending}
          >
            {grantPremiumMutation.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            Grant Premium
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// =============================================================================
// Delete Confirmation Dialog
// =============================================================================

interface DeleteUserDialogProps {
  user: UserItem | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

function DeleteUserDialog({ user, open, onOpenChange }: DeleteUserDialogProps) {
  const [hardDelete, setHardDelete] = useState(false)
  const deleteUserMutation = useDeleteUser()

  const handleSubmit = async () => {
    if (!user) return

    await deleteUserMutation.mutateAsync({
      userId: user.id,
      hardDelete,
    })
    onOpenChange(false)
    setHardDelete(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete User</DialogTitle>
          <DialogDescription>
            Are you sure you want to delete {user?.display_name || user?.email}?
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
            <p className="text-sm text-destructive">
              {hardDelete
                ? "This action is permanent and cannot be undone. All user data will be permanently deleted."
                : "The user account will be disabled but can be restored later."}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="hardDelete"
              checked={hardDelete}
              onChange={(e) => setHardDelete(e.target.checked)}
              className="rounded border-border"
            />
            <Label htmlFor="hardDelete" className="text-sm">
              Permanently delete user and all data
            </Label>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleSubmit}
            disabled={deleteUserMutation.isPending}
          >
            {deleteUserMutation.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            {hardDelete ? "Permanently Delete" : "Disable Account"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// =============================================================================
// User Actions Menu
// =============================================================================

interface UserActionsMenuProps {
  user: UserItem
  onViewDetails: () => void
  onChangeRole: () => void
  onToggleStatus: () => void
  onGrantPremium: () => void
  onRevokePremium: () => void
  onDelete: () => void
}

function UserActionsMenu({
  user,
  onViewDetails,
  onChangeRole,
  onToggleStatus,
  onGrantPremium,
  onRevokePremium,
  onDelete,
}: UserActionsMenuProps) {
  const updateStatusMutation = useUpdateUserStatus()
  const revokePremiumMutation = useRevokePremium()

  const handleToggleStatus = async () => {
    await updateStatusMutation.mutateAsync({
      userId: user.id,
      isActive: !user.is_active,
    })
    onToggleStatus()
  }

  const handleRevokePremium = async () => {
    await revokePremiumMutation.mutateAsync(user.id)
    onRevokePremium()
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>Actions</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={onViewDetails}>
          <Eye className="mr-2 h-4 w-4" />
          View Details
        </DropdownMenuItem>
        <DropdownMenuItem onClick={onChangeRole}>
          <UserCog className="mr-2 h-4 w-4" />
          Change Role
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handleToggleStatus}>
          {user.is_active ? (
            <>
              <Ban className="mr-2 h-4 w-4" />
              Disable Account
            </>
          ) : (
            <>
              <CheckCircle className="mr-2 h-4 w-4" />
              Enable Account
            </>
          )}
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        {user.role !== "premium" && user.role !== "admin" && (
          <DropdownMenuItem onClick={onGrantPremium}>
            <Gift className="mr-2 h-4 w-4" />
            Grant Premium
          </DropdownMenuItem>
        )}
        {user.role === "premium" && (
          <DropdownMenuItem onClick={handleRevokePremium}>
            <XCircle className="mr-2 h-4 w-4" />
            Revoke Premium
          </DropdownMenuItem>
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={onDelete} className="text-destructive">
          <Trash2 className="mr-2 h-4 w-4" />
          Delete User
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

// =============================================================================
// Main Page Component
// =============================================================================

export default function AdminUsersPage() {
  const [filters, setFilters] = useState<UserListFilters>({
    limit: 20,
    offset: 0,
    sort_by: "created_at",
    sort_order: "desc",
  })
  const [searchInput, setSearchInput] = useState("")

  // Dialog states
  const [detailsUserId, setDetailsUserId] = useState<string | null>(null)
  const [roleChangeUser, setRoleChangeUser] = useState<UserItem | null>(null)
  const [grantPremiumUser, setGrantPremiumUser] = useState<UserItem | null>(null)
  const [deleteUser, setDeleteUser] = useState<UserItem | null>(null)

  const { data, isLoading, refetch } = useAdminUsers(filters)

  // Debounced search using useCallback
  const debouncedSearch = useCallback(
    debounce((...args: unknown[]) => {
      const value = args[0] as string
      setFilters((f) => ({ ...f, search: value || undefined, offset: 0 }))
    }, 300),
    []
  )

  const handleSearchChange = (value: string) => {
    setSearchInput(value)
    debouncedSearch(value)
  }

  const handleFilterChange = (key: keyof UserListFilters, value: string | boolean | undefined) => {
    setFilters((f) => ({
      ...f,
      [key]: value === "" ? undefined : value,
      offset: 0,
    }))
  }

  const handleSort = (field: string) => {
    setFilters((f) => ({
      ...f,
      sort_by: field,
      sort_order: f.sort_by === field && f.sort_order === "asc" ? "desc" : "asc",
    }))
  }

  const handlePageChange = (direction: "prev" | "next") => {
    const newOffset = direction === "next"
      ? (filters.offset || 0) + (filters.limit || 20)
      : Math.max(0, (filters.offset || 0) - (filters.limit || 20))
    setFilters((f) => ({ ...f, offset: newOffset }))
  }

  const users = data?.users || []
  const total = data?.total || 0
  const currentPage = Math.floor((filters.offset || 0) / (filters.limit || 20)) + 1
  const totalPages = Math.ceil(total / (filters.limit || 20))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Manage Users</h1>
          <p className="text-muted-foreground">
            View and manage platform users ({total} total)
          </p>
        </div>
        <Button variant="outline" onClick={() => refetch()} className="gap-2">
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col gap-4 md:flex-row md:items-center">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search by email or name..."
                value={searchInput}
                onChange={(e) => handleSearchChange(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <Select
                value={filters.role || "all"}
                onValueChange={(v) => handleFilterChange("role", v === "all" ? undefined : v as UserRole)}
              >
                <SelectTrigger className="w-[130px]">
                  <Filter className="mr-2 h-4 w-4" />
                  <SelectValue placeholder="Role" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Roles</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                  <SelectItem value="premium">Premium</SelectItem>
                  <SelectItem value="free">Free</SelectItem>
                </SelectContent>
              </Select>
              <Select
                value={filters.is_active === undefined ? "all" : filters.is_active.toString()}
                onValueChange={(v) => handleFilterChange("is_active", v === "all" ? undefined : v === "true")}
              >
                <SelectTrigger className="w-[130px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="true">Active</SelectItem>
                  <SelectItem value="false">Disabled</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* User List */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex h-64 items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : users.length === 0 ? (
            <div className="flex h-64 flex-col items-center justify-center text-muted-foreground">
              <User className="mb-4 h-12 w-12" />
              <p>No users found</p>
              {searchInput && (
                <p className="text-sm">Try adjusting your search or filters</p>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b bg-muted/50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium">
                      <button
                        className="flex items-center gap-1 hover:text-foreground"
                        onClick={() => handleSort("email")}
                      >
                        User
                        <ArrowUpDown className="h-3 w-3" />
                      </button>
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Role</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">
                      <button
                        className="flex items-center gap-1 hover:text-foreground"
                        onClick={() => handleSort("created_at")}
                      >
                        Joined
                        <ArrowUpDown className="h-3 w-3" />
                      </button>
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium">
                      <button
                        className="flex items-center gap-1 hover:text-foreground"
                        onClick={() => handleSort("last_login")}
                      >
                        Last Login
                        <ArrowUpDown className="h-3 w-3" />
                      </button>
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {users.map((user) => (
                    <tr key={user.id} className="hover:bg-muted/50">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <Avatar className="h-8 w-8">
                            <AvatarFallback>
                              {user.display_name?.[0] || user.email[0].toUpperCase()}
                            </AvatarFallback>
                          </Avatar>
                          <div>
                            <p className="font-medium">
                              {user.display_name || "No name"}
                            </p>
                            <p className="text-sm text-muted-foreground">
                              {user.email}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <RoleBadge role={user.role} />
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge isActive={user.is_active} />
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">
                        {formatDate(user.created_at)}
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">
                        {user.last_login ? formatRelativeTime(user.last_login) : "Never"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <UserActionsMenu
                          user={user}
                          onViewDetails={() => setDetailsUserId(user.id)}
                          onChangeRole={() => setRoleChangeUser(user)}
                          onToggleStatus={() => {}}
                          onGrantPremium={() => setGrantPremiumUser(user)}
                          onRevokePremium={() => {}}
                          onDelete={() => setDeleteUser(user)}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {users.length > 0 && (
            <div className="flex items-center justify-between border-t px-4 py-3">
              <p className="text-sm text-muted-foreground">
                Showing {(filters.offset || 0) + 1} to{" "}
                {Math.min((filters.offset || 0) + users.length, total)} of {total} users
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange("prev")}
                  disabled={currentPage === 1}
                >
                  <ChevronLeft className="h-4 w-4" />
                  Previous
                </Button>
                <span className="text-sm">
                  Page {currentPage} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange("next")}
                  disabled={!data?.has_more}
                >
                  Next
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Dialogs */}
      <UserDetailsDialog
        userId={detailsUserId}
        open={!!detailsUserId}
        onOpenChange={(open) => !open && setDetailsUserId(null)}
      />
      <RoleChangeDialog
        user={roleChangeUser}
        open={!!roleChangeUser}
        onOpenChange={(open) => !open && setRoleChangeUser(null)}
      />
      <GrantPremiumDialog
        user={grantPremiumUser}
        open={!!grantPremiumUser}
        onOpenChange={(open) => !open && setGrantPremiumUser(null)}
      />
      <DeleteUserDialog
        user={deleteUser}
        open={!!deleteUser}
        onOpenChange={(open) => !open && setDeleteUser(null)}
      />
    </div>
  )
}
