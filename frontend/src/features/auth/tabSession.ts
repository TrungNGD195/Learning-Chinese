import { authApi } from './api'

// A non-sensitive document-lifetime marker only. Credentials remain HttpOnly
// cookies; no user identity, access token or refresh token is stored here.
export const tabSessionMarker = 'bo.tab-initialized.v1'

type TabStorage = Pick<Storage, 'getItem' | 'setItem'>

export function createTabSessionInitializer(storage: () => TabStorage, endSession: () => Promise<void>) {
  let prepared: Promise<void> | null = null
  return () => {
    if (!prepared) {
      prepared = Promise.resolve().then(async () => {
        const tab = storage()
        if (tab.getItem(tabSessionMarker) === 'ready') return
        // Never trust cookies left by an earlier tab. Finish logout before any
        // authenticated query or login form can mount. Reload retains the marker.
        await endSession()
        tab.setItem(tabSessionMarker, 'ready')
      }).catch((error: unknown) => {
        prepared = null
        throw error
      })
    }
    return prepared
  }
}

export const prepareTabSession = createTabSessionInitializer(() => window.sessionStorage, () => authApi.logout())
