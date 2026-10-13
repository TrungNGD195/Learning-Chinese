import { isRouteErrorResponse, Link, useRouteError } from 'react-router'

export function RouteErrorBoundary() {
  const error = useRouteError()
  const message = isRouteErrorResponse(error) ? `${error.status} ${error.statusText}` : 'An unexpected error occurred.'
  return <main className="page-container"><section className="screen" role="alert" data-testid="route-error-boundary">
    <h1>Something went wrong</h1><p>{message}</p><Link className="secondary-action" to="/dashboard">Return to Dashboard</Link>
  </section></main>
}
