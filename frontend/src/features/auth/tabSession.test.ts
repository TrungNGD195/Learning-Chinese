import { describe, expect, it, vi } from 'vitest'
import { createTabSessionInitializer, tabSessionMarker } from './tabSession'

function storage() {
  const rows = new Map<string, string>()
  return { getItem: vi.fn((key: string) => rows.get(key) ?? null), setItem: vi.fn((key: string, value: string) => { rows.set(key, value) }) }
}

describe('tab session initialization', () => {
  it('waits for server logout before marking a new tab ready and shares concurrent startup', async () => {
    const tab = storage()
    let finish!: () => void
    const logout = vi.fn(() => new Promise<void>(resolve => { finish = resolve }))
    const prepare = createTabSessionInitializer(() => tab, logout)
    const first = prepare(), second = prepare()
    expect(first).toBe(second)
    await Promise.resolve()
    expect(logout).toHaveBeenCalledOnce()
    expect(tab.setItem).not.toHaveBeenCalled()
    finish(); await first
    expect(tab.setItem).toHaveBeenCalledWith(tabSessionMarker, 'ready')
    await prepare()
    expect(logout).toHaveBeenCalledOnce()
  })

  it('preserves the session across a reload with the same tab storage', async () => {
    const tab = storage(), logout = vi.fn(async () => {})
    await createTabSessionInitializer(() => tab, logout)()
    const afterReload = createTabSessionInitializer(() => tab, logout)
    await afterReload()
    expect(logout).toHaveBeenCalledOnce()
  })

  it('does not reuse the prior tab cookies when a reopened tab has fresh storage', async () => {
    const logout = vi.fn(async () => {})
    await createTabSessionInitializer(storage, logout)()
    await createTabSessionInitializer(storage, logout)()
    expect(logout).toHaveBeenCalledTimes(2)
  })

  it('does not mark a failed logout successful and permits retry', async () => {
    const tab = storage(), logout = vi.fn().mockRejectedValueOnce(new Error('offline')).mockResolvedValue(undefined)
    const prepare = createTabSessionInitializer(() => tab, logout)
    await expect(prepare()).rejects.toThrow('offline')
    expect(tab.setItem).not.toHaveBeenCalled()
    await prepare()
    expect(logout).toHaveBeenCalledTimes(2)
    expect(tab.getItem(tabSessionMarker)).toBe('ready')
  })

  it('does not authorize rendering when browser tab storage is unavailable', async () => {
    const logout = vi.fn(async () => {})
    const prepare = createTabSessionInitializer(() => { throw new Error('blocked') }, logout)
    await expect(prepare()).rejects.toThrow('blocked')
    expect(logout).not.toHaveBeenCalled()
  })
})
