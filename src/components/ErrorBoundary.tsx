"use client";

import * as Sentry from "@sentry/nextjs";
import { Component, ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { AlertCircle } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  eventId?: string;
}

/**
 * Error Boundary component that catches React component errors
 * and reports them to Sentry
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log error to Sentry with component stack
    const eventId = Sentry.captureException(error, {
      contexts: {
        react: {
          componentStack: errorInfo.componentStack,
        },
      },
      tags: {
        error_boundary: "true",
      },
    });

    this.setState({ eventId });

    // Also log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error("Error caught by ErrorBoundary:", error);
      console.error("Component stack:", errorInfo.componentStack);
    }
  }

  render() {
    if (this.state.hasError) {
      // Render custom fallback UI or default error UI
      return this.props.fallback || (
        <Card className="p-8 m-4 max-w-2xl mx-auto mt-8">
          <div className="flex items-start gap-4">
            <AlertCircle className="h-8 w-8 text-destructive flex-shrink-0 mt-1" />
            <div className="flex-1">
              <h2 className="text-xl font-semibold mb-2">Something went wrong</h2>
              <p className="text-muted-foreground mb-4">
                We've been notified about this error and are working on a fix.
                You can try reloading the page or go back to the previous page.
              </p>
              <div className="flex gap-2">
                <Button
                  onClick={() => window.location.reload()}
                  variant="default"
                >
                  Reload Page
                </Button>
                <Button
                  variant="outline"
                  onClick={() => window.history.back()}
                >
                  Go Back
                </Button>
                {this.state.eventId && (
                  <Button
                    variant="outline"
                    onClick={() => {
                      if (this.state.eventId) {
                        Sentry.showReportDialog({
                          eventId: this.state.eventId,
                          title: "It looks like we're having issues.",
                          subtitle: "Our team has been notified. If you'd like to help, tell us what happened below.",
                          subtitle2: "We appreciate your feedback!",
                        });
                      }
                    }}
                  >
                    Report Issue
                  </Button>
                )}
              </div>
            </div>
          </div>
        </Card>
      );
    }

    return this.props.children;
  }
}
