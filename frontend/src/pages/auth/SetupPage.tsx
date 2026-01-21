/**
 * Setup Page
 * 
 * First-time setup wizard for the first user (becomes admin).
 */

import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { CheckCircle2, ArrowRight, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { apiClient } from "@/lib/api"
import toast from "react-hot-toast"

export default function SetupPage() {
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(false)
  const [isComplete, setIsComplete] = useState(false)

  const handleSetup = async () => {
    setIsLoading(true)
    try {
      await apiClient.post("/auth/setup")
      setIsComplete(true)
      toast.success("Setup complete! You are now the admin.")
      setTimeout(() => {
        navigate("/dashboard")
      }, 2000)
    } catch (error) {
      console.error("Setup error:", error)
      toast.error("Setup failed. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex flex-col items-center gap-8">
      {/* Logo */}
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-synthora shadow-lg shadow-primary/25">
          <span className="text-4xl font-bold text-white">S</span>
        </div>
        <h1 className="text-4xl font-bold tracking-tight text-gradient">
          Welcome to Synthora
        </h1>
        <p className="max-w-md text-lg text-muted-foreground">
          Let's set up your workspace
        </p>
      </div>

      {/* Setup card */}
      <Card className="w-full max-w-md glass-card">
        <CardHeader className="text-center">
          <CardTitle>Initial Setup</CardTitle>
          <CardDescription>
            You're the first user! You'll be set up as the administrator.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Setup steps */}
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-5 w-5 text-green-500" />
              <span className="text-sm">Create admin account</span>
            </div>
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-5 w-5 text-green-500" />
              <span className="text-sm">Initialize system settings</span>
            </div>
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-5 w-5 text-green-500" />
              <span className="text-sm">Load default templates</span>
            </div>
          </div>

          {/* Action button */}
          {isComplete ? (
            <div className="flex items-center justify-center gap-2 rounded-lg bg-green-500/10 p-4 text-green-500">
              <CheckCircle2 className="h-5 w-5" />
              <span className="font-medium">Setup complete! Redirecting...</span>
            </div>
          ) : (
            <Button
              size="lg"
              className="w-full gap-2"
              onClick={handleSetup}
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Setting up...
                </>
              ) : (
                <>
                  Complete Setup
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

