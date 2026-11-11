import { useEffect, useState, type PropsWithChildren } from 'react'
import { Alert, Button, LoadingState } from '../../components/ui'
import { prepareTabSession } from './tabSession'

export function TabSessionBoundary({ children }: PropsWithChildren) {
  const [state, setState] = useState<'loading' | 'ready' | 'failed'>('loading')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let current = true
    void prepareTabSession().then(
      () => { if (current) setState('ready') },
      () => { if (current) setState('failed') },
    )
    return () => { current = false }
  }, [attempt])
  if (state === 'ready') return children
  return <main className="page-container" aria-label="Kiểm tra phiên đăng nhập">
    {state === 'loading' ? <LoadingState>Đang kiểm tra phiên đăng nhập…</LoadingState> : <Alert role="alert" tone="error" action={<Button onClick={() => { setState('loading'); setAttempt(value => value + 1) }}>Thử lại</Button>}>Chưa thể mở phiên đăng nhập. Hãy kiểm tra kết nối và cho phép dữ liệu trang web trong trình duyệt, rồi thử lại.</Alert>}
  </main>
}
