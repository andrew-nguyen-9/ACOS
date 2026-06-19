import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}
interface State {
  hasError: boolean;
  message: string;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: "" };

  static getDerivedStateFromError(err: Error): State {
    return { hasError: true, message: err.message };
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="flex flex-col items-center justify-center h-full gap-3 p-8">
            <p className="font-semibold text-red-400">Something went wrong</p>
            <p className="text-[#a1a1a1] text-sm font-mono">{this.state.message}</p>
            <button
              className="mt-2 px-4 py-2 rounded-xl bg-white/[0.08] text-neutral-200 text-sm hover:bg-white/[0.12] transition-colors"
              onClick={() => this.setState({ hasError: false, message: "" })}
            >
              Retry
            </button>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
