/* eslint-disable camelcase */
export async function bootstrapSession (summary) {
    const res = await fetch('/api/session/bootstrap', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ summary })
    })
    if (!res.ok) throw new Error('bootstrap failed')
    return await res.json() // { session_id }
}

export function chatSSE ({ sessionId, message, onEvent }) {
    const controller = new AbortController()
    const payload = { message }
    payload.session_id = sessionId
    fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
        body: JSON.stringify(payload),
        signal: controller.signal
    }).then(async (res) => {
        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        while (true) {
            const { value, done } = await reader.read()
            if (done) break
            buffer += decoder.decode(value, { stream: true })
            const parts = buffer.split('\n\n')
            buffer = parts.pop() || ''
            for (const raw of parts) {
                const lines = raw.split('\n')
                const ev = (lines.find(l => l.startsWith('event:')) || '').replace('event:', '').trim()
                const dataLine = (lines.find(l => l.startsWith('data:')) || '').replace('data:', '').trim()
                try { onEvent && onEvent({ event: ev, data: JSON.parse(dataLine) }) } catch { /* ignore */ }
            }
        }
    }).catch(() => {})
    return () => controller.abort()
}
