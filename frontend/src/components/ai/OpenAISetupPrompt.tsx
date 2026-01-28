/**
 * OpenAI Setup Prompt
 *
 * Shown when user hasn't configured their OpenAI integration.
 */

import { Link } from "react-router-dom"
import { Key, Settings, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export function OpenAISetupPrompt() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <Card className="max-w-md text-center">
        <CardHeader>
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted">
            <Key className="h-8 w-8 text-muted-foreground" />
          </div>
          <CardTitle>OpenAI Integration Required</CardTitle>
          <CardDescription>
            To use AI Suggestions, please configure your OpenAI API key in Settings.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2 text-left text-sm text-muted-foreground">
            <p className="flex items-start gap-2">
              <Sparkles className="h-4 w-4 mt-0.5 shrink-0 text-primary" />
              Generate personalized video ideas based on your analytics
            </p>
            <p className="flex items-start gap-2">
              <Sparkles className="h-4 w-4 mt-0.5 shrink-0 text-primary" />
              Chat with AI to refine and improve suggestions
            </p>
            <p className="flex items-start gap-2">
              <Sparkles className="h-4 w-4 mt-0.5 shrink-0 text-primary" />
              Create video series and monthly content plans
            </p>
          </div>
          <Link to="/settings">
            <Button className="w-full gap-2">
              <Settings className="h-4 w-4" />
              Go to Integrations
            </Button>
          </Link>
          <p className="text-xs text-muted-foreground">
            Don't have an OpenAI API key?{" "}
            <a
              href="https://platform.openai.com/api-keys"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline"
            >
              Get one here
            </a>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
