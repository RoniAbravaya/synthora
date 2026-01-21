/**
 * Login Page
 * 
 * Simple landing page with Google Sign-In.
 */

import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Chrome } from "lucide-react"
import { useAuth } from "@/contexts/AuthContext"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import toast from "react-hot-toast"

export default function LoginPage() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [isLoading, setIsLoading] = useState(false)

  const handleLogin = async () => {
    setIsLoading(true)
    try {
      await login()
      toast.success("Welcome to Synthora!")
      navigate("/dashboard")
    } catch (error) {
      console.error("Login error:", error)
      toast.error("Failed to sign in. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex flex-col items-center gap-8">
      {/* Logo and tagline */}
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-synthora shadow-lg shadow-primary/25 animate-pulse-glow">
          <span className="text-4xl font-bold text-white">S</span>
        </div>
        <h1 className="text-4xl font-bold tracking-tight text-gradient">
          Synthora
        </h1>
        <p className="max-w-md text-lg text-muted-foreground">
          AI-Powered Viral Video Generator. Create, schedule, and analyze your content.
        </p>
      </div>

      {/* Login card */}
      <Card className="w-full max-w-md glass-card animate-fade-in">
        <CardHeader className="text-center">
          <CardTitle>Get Started</CardTitle>
          <CardDescription>
            Sign in with your Google account to continue
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            variant="outline"
            size="xl"
            className="w-full gap-3"
            onClick={handleLogin}
            disabled={isLoading}
          >
            {isLoading ? (
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-current border-t-transparent" />
            ) : (
              <Chrome className="h-5 w-5" />
            )}
            {isLoading ? "Signing in..." : "Continue with Google"}
          </Button>
        </CardContent>
      </Card>

      {/* Features */}
      <div className="grid max-w-2xl grid-cols-3 gap-6 text-center animate-fade-in animation-delay-200">
        <div className="space-y-2">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg bg-glow-cyan/10 text-glow-cyan">
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </div>
          <h3 className="font-semibold">AI Video Generation</h3>
          <p className="text-sm text-muted-foreground">Create viral videos with AI</p>
        </div>
        <div className="space-y-2">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg bg-glow-violet/10 text-glow-violet">
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
          <h3 className="font-semibold">Smart Scheduling</h3>
          <p className="text-sm text-muted-foreground">Post at optimal times</p>
        </div>
        <div className="space-y-2">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg bg-glow-fuchsia/10 text-glow-fuchsia">
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <h3 className="font-semibold">Deep Analytics</h3>
          <p className="text-sm text-muted-foreground">Track your performance</p>
        </div>
      </div>

      {/* Footer */}
      <p className="text-xs text-muted-foreground animate-fade-in animation-delay-300">
        By signing in, you agree to our Terms of Service and Privacy Policy
      </p>
    </div>
  )
}

