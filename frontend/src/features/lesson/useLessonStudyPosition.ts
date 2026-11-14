import { useLayoutEffect, useRef } from 'react'

// Route changes focus the new material. Progress updates only resize chrome;
// they must never move the learner's reading position.
export function useLessonStudyPosition(ready: boolean, routeIdentity: string) {
  const root = useRef<HTMLElement>(null)
  useLayoutEffect(() => {
    const page = root.current
    if (!ready || !page) return
    const header = page.querySelector<HTMLElement>('.lesson-header')
    const index = page.querySelector<HTMLElement>('.lesson-sequence-nav')
    const study = page.querySelector<HTMLElement>('#lesson-study-content')
    const globalNav = document.querySelector<HTMLElement>('.academy-mobile-nav')
    const controls = page.querySelector<HTMLElement>('.vocabulary-page__navigation, .lesson-part-navigation')
    const compact = () => window.matchMedia?.('(max-width: 800px)').matches ?? window.innerWidth <= 800
    const measure = () => {
      page.style.setProperty('--lesson-header-height', `${header?.getBoundingClientRect().height ?? 0}px`)
      page.style.setProperty('--lesson-global-nav-height', `${globalNav?.getBoundingClientRect().height ?? 0}px`)
      page.style.setProperty('--lesson-controls-height', `${controls?.getBoundingClientRect().height ?? 76}px`)
    }
    measure()
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(measure)
    for (const item of [header, index, globalNav, controls]) if (item) observer?.observe(item)
    window.addEventListener('resize', measure)
    const position = () => {
      if (!study) return
      const headerHeight = header?.getBoundingClientRect().height ?? 0
      const navHeight = compact() || index?.classList.contains('pronunciation-sections-nav') || index?.classList.contains('lesson-sections-horizontal') ? index?.getBoundingClientRect().height ?? 0 : 0
      const top = Math.max(0, window.scrollY + study.getBoundingClientRect().top - headerHeight - navHeight - 20)
      if (Math.abs(window.scrollY - top) > 1) window.scrollTo({ top, behavior: 'instant' })
      const heading = study.querySelector<HTMLElement>('.vocabulary-study-card__identity h2') ?? study.querySelector<HTMLElement>('h2')
      heading?.setAttribute('tabindex', '-1')
      heading?.focus({ preventScroll: true })
      if (compact() && index) {
        const active = index.querySelector<HTMLElement>('[aria-current="page"]')
        if (active) {
          const bounds = index.getBoundingClientRect(), item = active.getBoundingClientRect()
          if (item.right > bounds.right) index.scrollLeft += item.right - bounds.right + 8
          else if (item.left < bounds.left) index.scrollLeft += item.left - bounds.left - 8
        }
      }
    }
    const frame = window.requestAnimationFrame(position)
    return () => { window.cancelAnimationFrame(frame); observer?.disconnect(); window.removeEventListener('resize', measure) }
  }, [ready, routeIdentity])
  return root
}
