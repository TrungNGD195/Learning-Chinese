import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { queryKeys } from '../../app/query/keys'
import { ApiError } from '../../lib/api/errors'
import { completeSection, getSections } from './api'
import { invalidatePronunciationCompletion } from './invalidation'

function sectionLabel(title: string | null, code: string) {
  return title?.trim() || code.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function completionErrorText(error: unknown) {
  if (error instanceof ApiError && (error.code === 'NETWORK_ERROR' || (error.status !== null && error.status >= 500))) {
    return 'A temporary problem prevented completion. Please try again.'
  }
  return 'Could not mark this section complete. Please try again.'
}

export function PronunciationPage() {
  const queryClient = useQueryClient()
  const [acknowledgement, setAcknowledgement] = useState('')
  const sectionsQuery = useQuery({ queryKey: queryKeys.pronunciation, queryFn: getSections })
  const completion = useMutation({
    mutationFn: completeSection,
    retry: false,
    onMutate: () => setAcknowledgement(''),
    onSuccess: async (_response, sectionId) => {
      await invalidatePronunciationCompletion(queryClient)
      const completedSection = queryClient.getQueryData<Awaited<ReturnType<typeof getSections>>>(queryKeys.pronunciation)
        ?.find((section) => section.id === sectionId)
      setAcknowledgement(completedSection ? `${sectionLabel(completedSection.title, completedSection.code)} marked complete.` : 'Pronunciation completion saved.')
    },
  })

  if (sectionsQuery.isPending && !sectionsQuery.data) {
    return <section className="screen" aria-labelledby="page-title"><h1 id="page-title">Pronunciation Foundations</h1><p role="status">Loading pronunciation sections…</p></section>
  }
  if (sectionsQuery.isError && !sectionsQuery.data) {
    return <section className="screen" aria-labelledby="page-title"><h1 id="page-title">Pronunciation Foundations</h1><p role="alert">Could not load pronunciation sections.</p><button type="button" onClick={() => void sectionsQuery.refetch()}>Retry</button></section>
  }

  return (
    <section className="screen" aria-labelledby="page-title">
      <h1 id="page-title">Pronunciation Foundations</h1>
      <p>Explore the three foundations of Chinese pronunciation.</p>
      {sectionsQuery.isFetching && <p role="status">Refreshing pronunciation progress…</p>}
      {sectionsQuery.isError && <p role="alert">Pronunciation progress could not be refreshed.</p>}
      {completion.isError && <p role="alert">{completionErrorText(completion.error)}</p>}
      {acknowledgement && <p role="status">{acknowledgement}</p>}
      <div className="section-grid">
        {(sectionsQuery.data ?? []).map((section) => {
          const label = sectionLabel(section.title, section.code)
          const completed = section.completed_at !== null
          return <section className="structural-card" key={section.id} aria-labelledby={`pronunciation-${section.id}`}>
            <h2 id={`pronunciation-${section.id}`}>{label}</h2>
            {section.description && <p>{section.description}</p>}
            {completed ? <p aria-label={`${label} completion state`}>Completed</p> : <button
              type="button"
              disabled={completion.isPending}
              onClick={() => completion.mutate(section.id)}
            >{completion.isPending && completion.variables === section.id ? 'Completing…' : `Mark ${label} complete`}</button>}
          </section>
        })}
      </div>
    </section>
  )
}
