/**
 * Chat Interface
 *
 * Conversational AI interface for refining suggestions,
 * creating series, and planning content.
 */

import { useState, useRef, useEffect } from "react"
import { Send, Bot, User } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { AIThinkingIndicator } from "./AIThinkingIndicator"
import { ActionCard } from "./ActionCard"
import type { ChatMessage, AISuggestionData, ActionCard as ActionCardType } from "@/types"

interface ChatInterfaceProps {
  messages: ChatMessage[]
  isLoading?: boolean
  onSendMessage: (message: string) => void
  onExecuteAction: (card: ActionCardType) => void
  suggestion?: AISuggestionData | null
}

export function ChatInterface({
  messages,
  isLoading = false,
  onSendMessage,
  onExecuteAction,
  suggestion,
}: ChatInterfaceProps) {
  const [inputValue, setInputValue] = useState("")
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (inputValue.trim() && !isLoading) {
      onSendMessage(inputValue.trim())
      setInputValue("")
    }
  }

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp)
      return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    } catch {
      return ""
    }
  }

  return (
    <Card className="mt-6">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <Bot className="h-5 w-5 text-primary" />
          AI Assistant
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Chat Messages */}
        <ScrollArea className="h-[400px] pr-4" ref={scrollRef}>
          <div className="space-y-4">
            {messages.map((message, index) => (
              <div
                key={index}
                className={cn(
                  "flex gap-3",
                  message.role === "user" ? "justify-end" : "justify-start"
                )}
              >
                {message.role === "assistant" && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                    <Bot className="h-4 w-4 text-primary" />
                  </div>
                )}
                <div
                  className={cn(
                    "max-w-[80%] space-y-2",
                    message.role === "user" ? "items-end" : "items-start"
                  )}
                >
                  <div
                    className={cn(
                      "rounded-lg px-4 py-2",
                      message.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted"
                    )}
                  >
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  </div>

                  {/* Action Cards */}
                  {message.action_cards && message.action_cards.length > 0 && (
                    <div className="space-y-2 mt-2">
                      {message.action_cards.map((card, cardIndex) => (
                        <ActionCard
                          key={cardIndex}
                          card={card}
                          onExecute={() => onExecuteAction(card)}
                        />
                      ))}
                    </div>
                  )}

                  <span className="text-xs text-muted-foreground">
                    {formatTimestamp(message.timestamp)}
                  </span>
                </div>
                {message.role === "user" && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted">
                    <User className="h-4 w-4" />
                  </div>
                )}
              </div>
            ))}

            {/* Loading indicator */}
            {isLoading && (
              <div className="flex gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                  <Bot className="h-4 w-4 text-primary" />
                </div>
                <div className="bg-muted rounded-lg px-4 py-3">
                  <AIThinkingIndicator />
                </div>
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Suggestion Prompts */}
        {messages.length <= 1 && suggestion && (
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onSendMessage("Create a 5-part series on this topic")}
              disabled={isLoading}
            >
              Create a series
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onSendMessage("Create a monthly content plan")}
              disabled={isLoading}
            >
              Monthly plan
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onSendMessage("Make it more engaging")}
              disabled={isLoading}
            >
              More engaging
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onSendMessage("Shorten the video to 30 seconds")}
              disabled={isLoading}
            >
              Make shorter
            </Button>
          </div>
        )}

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Ask me to refine, create a series, or plan content..."
            disabled={isLoading}
            className="flex-1"
          />
          <Button type="submit" disabled={isLoading || !inputValue.trim()}>
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
