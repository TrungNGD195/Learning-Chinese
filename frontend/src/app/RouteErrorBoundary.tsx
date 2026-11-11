import { Link } from 'react-router'
import { Alert, PageHeader, Surface } from '../components/ui'

export function RouteErrorBoundary() {
  return <main className="page-container shared-error-page shared-route-error-page" id="main-content" tabIndex={-1}><Surface as="section" className="screen public-route-error-page shared-error-card" data-testid="route-error-boundary" aria-labelledby="route-error-title" aria-describedby="route-error-description">
    <PageHeader title="Đã có sự cố xảy ra" titleId="route-error-title" />
    <Alert id="route-error-description" role="alert" tone="error">Đã xảy ra lỗi ngoài dự kiến. Vui lòng quay lại trang học tập và thử lại.</Alert>
    <Link className="secondary-action shared-error-recovery" to="/login">Về trang học tập</Link>
  </Surface></main>
}
