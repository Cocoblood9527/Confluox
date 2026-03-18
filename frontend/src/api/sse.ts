export type SseChunk = {
  event: string
  data: string
}

export type SseFrameBoundary = {
  index: number
  delimiterLength: 2 | 4
}

export function findNextSseFrameBoundary(
  pending: string,
): SseFrameBoundary | null {
  const lfBoundary = pending.indexOf('\n\n')
  const crlfBoundary = pending.indexOf('\r\n\r\n')

  if (lfBoundary < 0 && crlfBoundary < 0) {
    return null
  }
  if (lfBoundary < 0) {
    return { index: crlfBoundary, delimiterLength: 4 }
  }
  if (crlfBoundary < 0) {
    return { index: lfBoundary, delimiterLength: 2 }
  }

  if (lfBoundary < crlfBoundary) {
    return { index: lfBoundary, delimiterLength: 2 }
  }
  return { index: crlfBoundary, delimiterLength: 4 }
}

export function parseSseFrame(frame: string): SseChunk | null {
  const normalized = frame.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  let event = 'message'
  const dataLines: string[] = []

  for (const line of normalized.split('\n')) {
    if (line.startsWith('event:')) {
      event = line.slice('event:'.length).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice('data:'.length).trimStart())
    }
  }

  if (dataLines.length === 0) {
    return null
  }

  return {
    event,
    data: dataLines.join('\n'),
  }
}
