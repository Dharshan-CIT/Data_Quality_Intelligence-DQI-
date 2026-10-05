import axios from 'axios'

function getSessionId() {
  let id = localStorage.getItem('dqi_session_id')
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem('dqi_session_id', id)
  }
  return id
}

export const sessionId = getSessionId()

export const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  config.headers['X-Session-Id'] = sessionId
  return config
})

export function wsUrl() {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${window.location.host}/ws/${sessionId}`
}
