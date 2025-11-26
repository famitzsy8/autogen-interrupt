import { Component, ErrorInfo, ReactNode } from 'react'

interface Props {
    children: ReactNode
}

interface State {
    hasError: boolean
    error: Error | null
    errorInfo: ErrorInfo | null
}

export class ErrorBoundary extends Component<Props, State> {
    public state: State = {
        hasError: false,
        error: null,
        errorInfo: null
    }

    public static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error, errorInfo: null }
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        this.setState({ error, errorInfo })
    }

    public render() {
        if (this.state.hasError) {
            return (
                <div className="p-8 bg-red-900 text-white min-h-screen">
                    <h1 className="text-2xl font-bold mb-4">Something went wrong</h1>
                    <div className="bg-black/50 p-4 rounded overflow-auto font-mono text-sm">
                        <p className="text-red-300 font-bold mb-2">{this.state.error?.toString()}</p>
                        <pre className="whitespace-pre-wrap">{this.state.errorInfo?.componentStack}</pre>
                    </div>
                </div>
            )
        }

        return this.props.children
    }
}
