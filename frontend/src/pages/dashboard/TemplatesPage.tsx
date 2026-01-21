/**
 * Templates Page
 * 
 * Browse and manage video templates.
 */

import { useState } from "react"
import { Link } from "react-router-dom"
import {
  FileText,
  Plus,
  Loader2,
  Search,
  Copy,
  Trash2,
  MoreHorizontal,
  Clock,
  Palette,
  Volume2,
  Video,
  Star,
  Lock,
} from "lucide-react"
import { cn, formatRelativeTime } from "@/lib/utils"
import { useAuth, useIsPremium } from "@/contexts/AuthContext"
import { useTemplates, useDeleteTemplate, useDuplicateTemplate } from "@/hooks/useTemplates"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
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
import type { Template } from "@/types"
import toast from "react-hot-toast"

// =============================================================================
// Template Card Component
// =============================================================================

interface TemplateCardProps {
  template: Template
  onUse: () => void
  onDuplicate: () => void
  onDelete?: () => void
  canDelete: boolean
}

function TemplateCard({
  template,
  onUse,
  onDuplicate,
  onDelete,
  canDelete,
}: TemplateCardProps) {
  const config = template.config

  return (
    <Card className="group relative overflow-hidden transition-all hover:border-primary/50">
      {/* System badge */}
      {template.is_system && (
        <div className="absolute right-2 top-2 z-10 flex items-center gap-1 rounded bg-primary/10 px-2 py-0.5 text-xs text-primary">
          <Star className="h-3 w-3" />
          System
        </div>
      )}

      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <FileText className="h-4 w-4 text-primary" />
          {template.name}
        </CardTitle>
        <CardDescription className="line-clamp-2">
          {template.description || "No description"}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Quick Stats */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Clock className="h-3 w-3" />
            {config.video_structure.duration_seconds}s
          </div>
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Video className="h-3 w-3" />
            {config.video_structure.aspect_ratio}
          </div>
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Palette className="h-3 w-3" />
            {config.visual_style.color_scheme}
          </div>
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Volume2 className="h-3 w-3" />
            {config.audio.voice_style}
          </div>
        </div>

        {/* Category & Tone */}
        <div className="flex flex-wrap gap-1">
          <span className="rounded bg-muted px-2 py-0.5 text-xs">
            {template.category}
          </span>
          <span className="rounded bg-muted px-2 py-0.5 text-xs">
            {config.script_prompt.tone}
          </span>
          <span className="rounded bg-muted px-2 py-0.5 text-xs">
            {config.platform_optimization.primary_platform}
          </span>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <Button size="sm" className="flex-1" onClick={onUse}>
            Use Template
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="icon" className="h-8 w-8">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={onDuplicate}>
                <Copy className="mr-2 h-4 w-4" />
                Duplicate
              </DropdownMenuItem>
              {canDelete && onDelete && (
                <DropdownMenuItem
                  className="text-destructive"
                  onClick={onDelete}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardContent>
    </Card>
  )
}

// =============================================================================
// Template Detail Dialog
// =============================================================================

interface TemplateDetailDialogProps {
  template: Template | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onUse: () => void
}

function TemplateDetailDialog({
  template,
  open,
  onOpenChange,
  onUse,
}: TemplateDetailDialogProps) {
  if (!template) return null

  const config = template.config

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            {template.name}
          </DialogTitle>
          <DialogDescription>{template.description}</DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 py-4 md:grid-cols-2">
          {/* Video Structure */}
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Video Structure</h4>
            <div className="space-y-1 text-sm text-muted-foreground">
              <p>Duration: {config.video_structure.duration_seconds}s</p>
              <p>Aspect Ratio: {config.video_structure.aspect_ratio}</p>
              <p>Segments: {config.video_structure.segments.length}</p>
            </div>
          </div>

          {/* Visual Style */}
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Visual Style</h4>
            <div className="space-y-1 text-sm text-muted-foreground">
              <p>Color Scheme: {config.visual_style.color_scheme}</p>
              <p>Font: {config.visual_style.font_family}</p>
              <p>Transitions: {config.visual_style.transition_style}</p>
            </div>
          </div>

          {/* Audio */}
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Audio</h4>
            <div className="space-y-1 text-sm text-muted-foreground">
              <p>Voice: {config.audio.voice_style}</p>
              <p>Music: {config.audio.background_music_genre}</p>
              <p>Sound Effects: {config.audio.sound_effects ? "Yes" : "No"}</p>
            </div>
          </div>

          {/* Script */}
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Script Style</h4>
            <div className="space-y-1 text-sm text-muted-foreground">
              <p>Tone: {config.script_prompt.tone}</p>
              <p>Hook: {config.script_prompt.hook_style}</p>
              <p>CTA: {config.script_prompt.call_to_action}</p>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          <Button onClick={onUse}>Use Template</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// =============================================================================
// Main Page Component
// =============================================================================

export default function TemplatesPage() {
  const { user } = useAuth()
  const isPremium = useIsPremium()

  const [search, setSearch] = useState("")
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null)
  const [deleteId, setDeleteId] = useState<string | null>(null)

  const { data, isLoading } = useTemplates()
  const deleteMutation = useDeleteTemplate()
  const duplicateMutation = useDuplicateTemplate()

  const allTemplates = data?.templates || []

  // Filter templates
  const filteredTemplates = allTemplates.filter(
    (t) =>
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.description?.toLowerCase().includes(search.toLowerCase()) ||
      t.category.toLowerCase().includes(search.toLowerCase())
  )

  const systemTemplates = filteredTemplates.filter((t) => t.is_system)
  const userTemplates = filteredTemplates.filter((t) => !t.is_system)

  const handleUseTemplate = (template: Template) => {
    // Navigate to create page with template pre-selected
    window.location.href = `/create?template=${template.id}`
  }

  const handleDuplicate = async (template: Template) => {
    await duplicateMutation.mutateAsync({
      id: template.id,
      name: `${template.name} (Copy)`,
    })
  }

  const handleDelete = async () => {
    if (!deleteId) return
    await deleteMutation.mutateAsync(deleteId)
    setDeleteId(null)
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
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Templates</h1>
          <p className="text-muted-foreground">
            Choose a template to create your video
          </p>
        </div>
        <div className="flex gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search templates..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-64 pl-9"
            />
          </div>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="all">
        <TabsList>
          <TabsTrigger value="all">
            All ({filteredTemplates.length})
          </TabsTrigger>
          <TabsTrigger value="system">
            System ({systemTemplates.length})
          </TabsTrigger>
          <TabsTrigger value="personal">
            My Templates ({userTemplates.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="mt-6">
          {filteredTemplates.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <FileText className="h-12 w-12 text-muted-foreground" />
                <h3 className="mt-4 text-lg font-medium">No templates found</h3>
                <p className="text-sm text-muted-foreground">
                  {search ? "Try a different search term" : "No templates available"}
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {filteredTemplates.map((template) => (
                <TemplateCard
                  key={template.id}
                  template={template}
                  onUse={() => handleUseTemplate(template)}
                  onDuplicate={() => handleDuplicate(template)}
                  onDelete={() => setDeleteId(template.id)}
                  canDelete={!template.is_system && template.id !== undefined}
                />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="system" className="mt-6">
          {systemTemplates.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <FileText className="h-12 w-12 text-muted-foreground" />
                <h3 className="mt-4 text-lg font-medium">No system templates</h3>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {systemTemplates.map((template) => (
                <TemplateCard
                  key={template.id}
                  template={template}
                  onUse={() => handleUseTemplate(template)}
                  onDuplicate={() => handleDuplicate(template)}
                  canDelete={false}
                />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="personal" className="mt-6">
          {userTemplates.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <FileText className="h-12 w-12 text-muted-foreground" />
                <h3 className="mt-4 text-lg font-medium">No personal templates</h3>
                <p className="text-sm text-muted-foreground">
                  Duplicate a system template to customize it
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {userTemplates.map((template) => (
                <TemplateCard
                  key={template.id}
                  template={template}
                  onUse={() => handleUseTemplate(template)}
                  onDuplicate={() => handleDuplicate(template)}
                  onDelete={() => setDeleteId(template.id)}
                  canDelete={true}
                />
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Template Detail Dialog */}
      <TemplateDetailDialog
        template={selectedTemplate}
        open={!!selectedTemplate}
        onOpenChange={(open) => !open && setSelectedTemplate(null)}
        onUse={() => {
          if (selectedTemplate) {
            handleUseTemplate(selectedTemplate)
          }
        }}
      />

      {/* Delete Confirmation */}
      <Dialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Template</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this template? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteId(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
