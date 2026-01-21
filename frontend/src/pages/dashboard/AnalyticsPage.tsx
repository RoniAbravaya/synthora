/**
 * Analytics Page
 * 
 * View performance analytics.
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export default function AnalyticsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
        <p className="text-muted-foreground">
          Track your content performance
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>No Data Yet</CardTitle>
          <CardDescription>
            Analytics will appear here once you start posting.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Connect social accounts and publish content to see analytics.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

