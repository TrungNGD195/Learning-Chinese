import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { useBeforeUnload, useBlocker } from 'react-router'
import { Dialog } from '../../components/ui/Dialog'

type Drafts = Record<string, boolean>
const DraftContext = createContext<{ report: (id: string, dirty: boolean) => void; dirty: boolean } | null>(null)

export function AuthoringSession({ children }: { children: ReactNode }) {
  const [drafts, setDrafts] = useState<Drafts>({})
  const report = useCallback((id: string, dirty: boolean) => setDrafts((previous) => previous[id] === dirty ? previous : { ...previous, [id]: dirty }), [])
  const dirty = Object.values(drafts).some(Boolean)
  const blocker = useBlocker(dirty)
  useBeforeUnload(useCallback((event) => { if (dirty) { event.preventDefault(); event.returnValue = '' } }, [dirty]))
  return <DraftContext.Provider value={{ report, dirty }}>{children}
    <Dialog cancelLabel="Hủy" open={blocker.state === 'blocked'} title="Rời trang khi chưa lưu?" confirmLabel="Rời trang" confirmVariant="danger" onConfirm={() => blocker.state === 'blocked' && blocker.proceed()} onCancel={() => blocker.state === 'blocked' && blocker.reset()} onClose={() => blocker.state === 'blocked' && blocker.reset()}>Nội dung chưa lưu sẽ bị mất. Bạn có thể quay lại biên soạn để lưu từng mục.</Dialog>
  </DraftContext.Provider>
}

export function useAuthoringDirty(id: string, dirty: boolean) {
  const context = useContext(DraftContext)
  const report = context?.report
  useEffect(() => { report?.(id, dirty); return () => report?.(id, false) }, [report, id, dirty])
}

export function useHasUnsavedDrafts() { return useContext(DraftContext)?.dirty ?? false }

export function AuthoringNotice() {
  const dirty = useHasUnsavedDrafts()
  return <div className={`admin-studio-save-state ${dirty ? 'has-changes' : ''}`} role="status">{dirty ? 'Có thay đổi chưa lưu · Lưu tại mục đang biên soạn' : 'Chọn một mục để biên soạn và xem trước'}<span>Xem trước chỉ hiển thị trong quản trị.</span></div>
}
