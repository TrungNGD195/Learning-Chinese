/** Match the latest completed zhong in this device voice, within 25 ms. */
export function ongClipForDuration(seconds = .55) {
  const valid = Number.isFinite(seconds) && seconds > 0 ? seconds : .55
  const milliseconds = Math.max(250, Math.min(1250, Math.round(valid * 20) * 50))
  return `/academy/audio/isolated-finals-v4/ong-${milliseconds}.wav`
}
