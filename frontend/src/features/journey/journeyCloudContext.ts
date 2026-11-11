import { createContext, useContext } from 'react'
export type CloudTrip = { destination: string; depart?: () => void; relocate?: () => void; cancelled?: () => void; prepare?: Promise<unknown>; short?: boolean; returning?: boolean; coverDelay?: number }
export type CloudTravel = (trip: CloudTrip) => boolean
export const JourneyCloudContext = createContext<{ travel: CloudTravel; cancel: () => void } | null>(null)
export const useJourneyCloud = () => useContext(JourneyCloudContext)
