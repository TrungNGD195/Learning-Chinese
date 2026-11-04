import { createContext } from 'react'
export type LearningScene = 'greeting' | 'family' | 'study' | 'path' | 'practice' | 'library'
export const ArtworkContext = createContext<{ scene: LearningScene; admin: boolean } | null>(null)
