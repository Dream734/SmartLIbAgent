import request from '@/utils/request'
import { getToken } from '@/utils/auth'

//AI对话请求


export function chatApi(data) {
    return request({
      url: '/api/ai/chat',
      method: 'post',
      data,
      timeout: 300000
    })
}

// SSE 流式对话：通过 fetch 读取 text/event-stream，逐 token 回调
export async function chatStream(data, { onThinking, onToken, onDone, onError, signal } = {}) {
  const token = getToken()
  const response = await fetch('/api/ai/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(data),
    signal
  })

  if (!response.ok || !response.body) {
    let message = '请求失败'
    try {
      const err = await response.json()
      message = err.message || err.detail || message
    } catch (e) {
      // 忽略非 JSON 响应
    }
    throw new Error(message)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  const dispatch = (line) => {
    const trimmed = line.trim()
    if (!trimmed.startsWith('data:')) return
    const payload = trimmed.slice(5).trim()
    if (!payload) return

    let event
    try {
      event = JSON.parse(payload)
    } catch (e) {
      return
    }

    if (event.type === 'thinking' && onThinking) {
      onThinking(event.content)
    } else if (event.type === 'token' && onToken) {
      onToken(event.content)
    } else if (event.type === 'done' && onDone) {
      onDone(event.message)
    } else if (event.type === 'error' && onError) {
      onError(event.message)
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let idx
    while ((idx = buffer.indexOf('\n\n')) !== -1) {
      const chunk = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)
      chunk.split('\n').forEach(dispatch)
    }
  }

  buffer.split('\n').forEach(dispatch)
}
