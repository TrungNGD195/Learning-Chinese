import { useEffect, useId, useSyncExternalStore } from 'react'
import { loadPronunciationRecording } from '../api/client'

type Input = { hanzi?: string; clip?: string; rate?: 0.8 | 1 }
type State = { voice: SpeechSynthesisVoice | null; owner: string | null; speaking: boolean; error: string | null; zhongReference: { seconds: number; voiceName: string } | null }
const empty: State = { voice: null, owner: null, speaking: false, error: null, zhongReference: null }
let state = empty
let engine: SpeechSynthesis | null = null
let active: SpeechSynthesisUtterance | null = null
let recordingContext: AudioContext | null = null
let recordingOutput: GainNode | null = null
let activeRecording: AudioBufferSourceNode | null = null
let recordingAbort: AbortController | null = null
let recordingGeneration = 0
const recordingBuffers = new Map<string, AudioBuffer>()
let users = 0
const listeners = new Set<() => void>()
const missingVoiceMessage = 'Thiết bị chưa có giọng đọc tiếng Trung. Hãy bật giọng tiếng Trung trong cài đặt giọng nói rồi thử lại.'
function update(next: State) { state = next; listeners.forEach(listener => listener()) }
function subscribe(listener: () => void) { listeners.add(listener); return () => { listeners.delete(listener) } }

// Match the deployed app: Mandarin only, prefer an installed/local voice.
function refreshVoice() {
  let voices: SpeechSynthesisVoice[] = []
  try { voices = engine?.getVoices().filter(voice => /^(cmn|zh-(cn|sg|tw|hans))(?:-|$)/i.test(voice.lang)) ?? [] } catch { /* Remain unavailable. */ }
  const voice = voices.find(voice => voice.localService) ?? voices[0] ?? null
  update({ ...state, voice, error: voice && state.error === missingVoiceMessage ? null : state.error })
}
function stop() {
  const hadActive = active !== null
  active = null
  recordingGeneration++
  recordingAbort?.abort()
  recordingAbort = null
  const recording = activeRecording
  activeRecording = null
  if (recording) {
    recording.onended = null
    try { recording.stop(); recording.disconnect() } catch { /* Already finished. */ }
  }
  if (hadActive) { try { engine?.cancel() } catch { /* Already stopped. */ } }
  update({ ...state, owner: null, speaking: false, error: null })
}

async function playRecording(clip: string, owner: string, generation: number) {
  try {
    // Keep a single output graph open between samples. Decode the complete file
    // before starting; no detached HTMLAudioElement, streaming or per-clip close.
    if (!recordingContext || recordingContext.state === 'closed') {
      recordingContext = new AudioContext({ latencyHint: 'playback' })
      recordingOutput = recordingContext.createGain()
      recordingOutput.gain.value = 1
      recordingOutput.connect(recordingContext.destination)
    }
    const context = recordingContext
    // Called within the click handler before the first fetch/await (autoplay).
    if (context.state === 'suspended') await context.resume()
    if (generation !== recordingGeneration) return
    let buffer = recordingBuffers.get(clip)
    if (!buffer) {
      const controller = new AbortController()
      recordingAbort = controller
      const bytes = await loadPronunciationRecording(clip, controller.signal)
      if (generation !== recordingGeneration) return
      buffer = await context.decodeAudioData(bytes)
      if (generation !== recordingGeneration || context !== recordingContext) return
      recordingBuffers.set(clip, buffer)
      if (recordingAbort === controller) recordingAbort = null
    }
    if (generation !== recordingGeneration || state.owner !== owner) return
    const source = context.createBufferSource()
    source.buffer = buffer
    source.playbackRate.value = 1
    source.connect(recordingOutput!)
    activeRecording = source
    source.onended = () => {
      if (activeRecording !== source || generation !== recordingGeneration) return
      activeRecording = null
      source.onended = null
      source.disconnect()
      // Do not close/suspend the output device at the end of a syllable.
      update({ ...state, owner, speaking: false, error: null })
    }
    source.start()
  } catch {
    if (generation !== recordingGeneration) return
    activeRecording?.disconnect()
    activeRecording = null
    recordingAbort = null
    update({ ...state, owner, speaking: false, error: 'Chưa thể phát bản thu. Bạn hãy bấm nghe lại.' })
  }
}

function speak(input: Input, owner: string) {
  stop()
  if (input.clip) {
    // File playback is limited to configured pronunciation samples. Never
    // fall back to the reported-bad browser reading if a recording fails.
    const allowedPath = /^\/academy\/audio\/special-i-native-v7\/cmn-(zi|ci|si|zhi|chi|shi|ri)1\.wav$/.test(input.clip)
      || /^\/academy\/audio\/isolated-finals-v1\/(ai|eng|er)\.wav$/.test(input.clip)
      || /^\/academy\/audio\/isolated-finals-v4\/ong-(250|300|350|400|450|500|550|600|650|700|750|800|850|900|950|1000|1050|1100|1150|1200|1250)\.wav$/.test(input.clip)
    if (!allowedPath) {
      update({ ...state, owner, error: 'Bản âm mẫu này chưa được cấu hình để nghe.' })
      return
    }
    update({ ...state, owner, speaking: true, error: null })
    void playRecording(input.clip, owner, recordingGeneration)
    return
  }
  if (!engine || !state.voice || typeof SpeechSynthesisUtterance === 'undefined') {
    update({ ...state, owner, error: missingVoiceMessage })
    return
  }
  if (!input.hanzi?.trim()) {
    update({ ...state, owner, error: 'Chưa có nội dung tiếng Trung để nghe.' })
    return
  }
  const utterance = new SpeechSynthesisUtterance(input.hanzi)
  utterance.voice = state.voice
  utterance.lang = state.voice.lang
  // Existing lesson speech stays at .8; the isolated preview can compare the
  // voice's natural tempo without altering pitch or clipping the syllable.
  utterance.rate = input.rate === 1 ? 1 : 0.8
  utterance.pitch = 1
  utterance.volume = 1
  active = utterance
  update({ ...state, owner, speaking: true, error: null })
  let startedAt: number | null = null
  utterance.onstart = () => { if (active === utterance) startedAt = performance.now() }
  utterance.onend = event => {
    if (active !== utterance) return
    let seconds = event?.elapsedTime
    if (!(seconds >= .15 && seconds <= 2) && startedAt !== null) seconds = (performance.now() - startedAt) / 1000
    const zhongReference = input.hanzi?.trim() === '中' && utterance.rate === .8 && Number.isFinite(seconds) && seconds >= .15 && seconds <= 2
      ? { seconds, voiceName: utterance.voice!.name } : state.zhongReference
    active = null
    update({ ...state, owner, speaking: false, error: null, zhongReference })
  }
  utterance.onerror = event => {
    if (active !== utterance) return
    active = null
    update({ ...state, owner, speaking: false, error: ['canceled', 'interrupted'].includes(event.error) ? null : 'Chưa thể phát âm thanh. Bạn hãy bấm nghe lại.' })
  }
  try { engine.cancel(); engine.speak(utterance) } catch {
    if (active !== utterance) return
    active = null
    update({ ...state, owner, speaking: false, error: 'Chưa thể phát âm thanh. Bạn hãy bấm nghe lại.' })
  }
}

/** Browser/device Mandarin playback, matching the deployed voice selection and rate. */
export function useBrowserMandarinAudio() {
  const owner = useId()
  const current = useSyncExternalStore(subscribe, () => state, () => empty)
  useEffect(() => {
    users++
    if (users === 1 && typeof window !== 'undefined' && 'speechSynthesis' in window) {
      engine = window.speechSynthesis
      refreshVoice()
      engine.addEventListener('voiceschanged', refreshVoice)
    }
    const hidden = () => { if (document.hidden && state.owner === owner) stop() }
    document.addEventListener('visibilitychange', hidden)
    return () => {
      document.removeEventListener('visibilitychange', hidden)
      if (state.owner === owner) stop()
      users--
      if (users === 0) {
        engine?.removeEventListener('voiceschanged', refreshVoice)
        engine = null
        const context = recordingContext
        recordingContext = null
        recordingOutput = null
        recordingBuffers.clear()
        if (context && context.state !== 'closed') void context.close().catch(() => { /* Page already closed. */ })
        update(empty)
      }
    }
  }, [owner])
  return {
    zhongReference: current.zhongReference,
    voiceName: current.voice?.name ?? null,
    voiceAvailable: current.voice !== null && typeof SpeechSynthesisUtterance !== 'undefined',
    speak: (input: Input) => speak(input, owner),
    isSpeaking: current.owner === owner && current.speaking,
    speechError: current.owner === owner ? current.error : null,
  }
}
