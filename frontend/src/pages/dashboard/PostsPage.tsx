/**
 * Posts Page
 * 
 * Manage social media posts.
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export default function PostsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Posts</h1>
        <p className="text-muted-foreground">
          Manage your social media posts
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>No Posts Yet</CardTitle>
          <CardDescription>
            Your posts will appear here.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Generate a video and post it to see your posts here.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

