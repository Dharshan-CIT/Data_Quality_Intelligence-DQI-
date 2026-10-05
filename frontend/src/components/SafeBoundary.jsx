import { Component } from 'react'

/** Contains crashes from a single visual (e.g. a WebGL canvas) so the rest of the page keeps working. */
export default class SafeBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { failed: false }
  }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidUpdate(prev) {
    if (prev.resetKey !== this.props.resetKey && this.state.failed) {
      this.setState({ failed: false })
    }
  }

  render() {
    if (this.state.failed) {
      return (
        <div className="w-full h-[420px] rounded-xl border border-border flex items-center justify-center text-sm text-text-secondary">
          3D view unavailable on this device. The charts below still show the same data.
        </div>
      )
    }
    return this.props.children
  }
}
