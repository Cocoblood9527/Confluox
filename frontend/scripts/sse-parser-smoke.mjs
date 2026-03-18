import assert from 'node:assert/strict'
import { findNextSseFrameBoundary, parseSseFrame } from '../src/api/sse.ts'

{
  const boundary = findNextSseFrameBoundary('event: a\ndata: one\n\nrest')
  assert.deepEqual(boundary, { index: 18, delimiterLength: 2 })
}

{
  const boundary = findNextSseFrameBoundary('event: a\r\ndata: one\r\n\r\nrest')
  assert.deepEqual(boundary, { index: 19, delimiterLength: 4 })
}

{
  const frame = parseSseFrame('event: chunk\r\ndata: hello\r\ndata: world\r\n')
  assert.deepEqual(frame, { event: 'chunk', data: 'hello\nworld' })
}

{
  const chunks = [
    'event: chunk\r\ndata: one\r\n\r\n',
    'event: chunk\r\ndata: two\r\n\r\n',
    'event: complete\r\ndata: done\r\n\r\n',
  ]
  const received = []
  let pending = ''

  for (const chunk of chunks) {
    pending += chunk
    let boundary = findNextSseFrameBoundary(pending)
    while (boundary !== null) {
      const frame = pending.slice(0, boundary.index)
      pending = pending.slice(boundary.index + boundary.delimiterLength)
      const parsed = parseSseFrame(frame)
      if (parsed) {
        received.push(parsed)
      }
      boundary = findNextSseFrameBoundary(pending)
    }
  }

  assert.equal(received.length, 3)
  assert.equal(received[2]?.event, 'complete')
  assert.equal(received[2]?.data, 'done')
}

console.log('sse parser smoke passed')
