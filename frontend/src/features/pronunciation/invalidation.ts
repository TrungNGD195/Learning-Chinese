import type { QueryClient } from '@tanstack/react-query'
import { queryKeys } from '../../app/query/keys'

export function invalidatePronunciationCompletion(queryClient: QueryClient) {
  return Promise.all([
    queryKeys.pronunciation,
    queryKeys.dashboard,
    queryKeys.curriculumLevels,
    queryKeys.curriculumHskRoot,
    queryKeys.progressOverview,
    queryKeys.progressHskRoot,
  ].map((queryKey) => queryClient.invalidateQueries({ queryKey })))
}
