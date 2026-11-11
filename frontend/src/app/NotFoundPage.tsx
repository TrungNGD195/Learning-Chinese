import { PageHeader, Surface } from '../components/ui'

export function NotFoundPage() {
  return (
    <main className="page-container not-found shared-error-page shared-not-found-page" id="main-content" data-testid="not-found" tabIndex={-1}>
      <Surface as="section" className="shared-error-card" aria-labelledby="not-found-title" aria-describedby="not-found-description">
        <PageHeader title="Không tìm thấy trang" titleId="not-found-title" />
        <p id="not-found-description" className="shared-error-message">Trang này không có trong ứng dụng hiện tại.</p>
      </Surface>
    </main>
  )
}
