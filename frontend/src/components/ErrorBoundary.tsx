import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'
import { Button } from '@/components/ui/button'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(_error: Error, _errorInfo: ErrorInfo) {}

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6 text-center">
          <h2 className="text-lg font-medium">Something went wrong</h2>
          <p className="text-muted-foreground">{this.state.error?.message ?? 'Unknown error'}</p>
          <Button onClick={() => this.setState({ hasError: false, error: null })} variant="outline" size="sm">
            Refresh
          </Button>
        </div>
      )
    }
    return this.props.children
  }
}
