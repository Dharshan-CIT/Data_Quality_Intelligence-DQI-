import { createContext, useContext, useEffect, useRef, useState } from 'react'
import { wsUrl } from '../api/client'

const SocketContext = createContext(null)

export function SocketProvider({ children }) {
  const wsRef = useRef(null)
  const listenersRef = useRef(new Map()) // type -> Set<callback>
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    let cancelled = false
    let retryTimer = null

    function connect() {
      const ws = new WebSocket(wsUrl())
      wsRef.current = ws

      ws.onopen = () => !cancelled && setConnected(true)
      ws.onclose = () => {
        if (cancelled) return
        setConnected(false)
        retryTimer = setTimeout(connect, 1500)
      }
      ws.onerror = () => ws.close()
      ws.onmessage = (event) => {
        let msg
        try {
          msg = JSON.parse(event.data)
        } catch {
          return
        }
        const callbacks = listenersRef.current.get(msg.type)
        if (callbacks) callbacks.forEach((cb) => cb(msg))
        const allCallbacks = listenersRef.current.get('*')
        if (allCallbacks) allCallbacks.forEach((cb) => cb(msg))
      }
    }
    connect()

    return () => {
      cancelled = true
      if (retryTimer) clearTimeout(retryTimer)
      wsRef.current?.close()
    }
  }, [])

  function send(obj) {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj))
  }

  function subscribe(type, callback) {
    if (!listenersRef.current.has(type)) listenersRef.current.set(type, new Set())
    listenersRef.current.get(type).add(callback)
    return () => listenersRef.current.get(type)?.delete(callback)
  }

  return (
    <SocketContext.Provider value={{ connected, send, subscribe }}>
      {children}
    </SocketContext.Provider>
  )
}

export function useSocket() {
  return useContext(SocketContext)
}
