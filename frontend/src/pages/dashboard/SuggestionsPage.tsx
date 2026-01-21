/**
 * Suggestions Page
 * 
 * AI-powered suggestions (premium feature).
 */

import { useIsPremium } from "@/contexts/AuthContext"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Link } from "react-router-dom"
import { Sparkles, Lock } from "lucide-react"

export default function SuggestionsPage() {
  const isPremium = useIsPremium()

  if (!isPremium) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Card className="max-w-md text-center">
          <CardHeader>
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-synthora">
              <Lock className="h-8 w-8 text-white" />
            </div>
            <CardTitle>Premium Feature</CardTitle>
            <CardDescription>
              AI Suggestions is available for Premium users only.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link to="/settings">
              <Button className="gap-2">
                <Sparkles className="h-4 w-4" />
                Upgrade to Premium
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">AI Suggestions</h1>
        <p className="text-muted-foreground">
          Personalized recommendations to improve your content
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Coming Soon</CardTitle>
          <CardDescription>
            AI suggestions will be implemented in the next section.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            This page will show AI-powered recommendations for posting times, content ideas, and more.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

