/* Chat API helper – minimal wrapper around fetch to talk to the FastAPI backend. */

const BASE_URL = process.env.VUE_APP_BACKEND_URL || 'http://localhost:8000'

export async function uploadLog(file) {
    const formData = new FormData()
    formData.append('file', file)

    const res = await fetch(`${BASE_URL}/upload-log`, {
        method: 'POST',
        body: formData
    })

    if (!res.ok) {
        const txt = await res.text()
        throw new Error(`upload-log failed: ${res.status} ${txt}`)
    }

    return res.json() // { session_id, ... }
}

export async function sendChat({ sessionId, message, conversationId }) {
    const payload = {
        session_id: sessionId, // eslint-disable-line camelcase
        message
    }
    if (conversationId) payload.conversation_id = conversationId // eslint-disable-line camelcase

    const res = await fetch(`${BASE_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })

    if (!res.ok) {
        const txt = await res.text()
        throw new Error(`chat failed: ${res.status} ${txt}`)
    }

    return res.json() // { response, conversation_id, ... }
}

// Poll session status
export async function getSessionStatus(sessionId) {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}`)
    if (!res.ok) throw new Error(`status fetch failed: ${res.status}`)
    return res.json() // { status: "completed"|... }
}
