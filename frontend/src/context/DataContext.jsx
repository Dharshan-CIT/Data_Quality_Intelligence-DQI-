import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api } from '../api/client'
import { useSocket } from './SocketContext'

const DataContext = createContext(null)

export function DataProvider({ children }) {
  const { subscribe, send } = useSocket()
  const [datasets, setDatasets] = useState([])
  const [active, setActiveState] = useState(null)
  const [loading, setLoading] = useState(false)
  // Lives here (not in the upload panel) so it survives the pipeline view replacing the dashboard.
  const [queue, setQueue] = useState([])

  const updateQueue = useCallback((name, status, detail = '') => {
    setQueue((q) => q.map((item) => (item.name === name ? { ...item, status, detail } : item)))
  }, [])

  const refresh = useCallback(async () => {
    const { data } = await api.get('/datasets')
    setDatasets(data.datasets)
    setActiveState(data.active)
    return data
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  useEffect(() => {
    return subscribe('dataset_updated', () => refresh())
  }, [subscribe, refresh])

  const setActive = useCallback(async (filename) => {
    await api.post(`/datasets/active/${encodeURIComponent(filename)}`)
    await refresh()
  }, [refresh])

  /**
   * Uploads files one at a time (the backend processes each synchronously),
   * tracking per-file status in `queue`. The last successful file becomes
   * active and its pipeline is streamed live.
   */
  const uploadFiles = useCallback(async (files) => {
    setLoading(true)
    setQueue(files.map((f) => ({ name: f.name, status: 'queued', detail: '' })))
    const uploaded = []
    try {
      for (const file of files) {
        updateQueue(file.name, 'uploading')
        try {
          const form = new FormData()
          form.append('file', file)
          const { data } = await api.post('/datasets/upload', form)
          uploaded.push(data.dataset.filename)
          updateQueue(file.name, 'done', data.warnings?.join('; ') || `${data.dataset.rows.toLocaleString()} rows`)
        } catch (e) {
          updateQueue(file.name, 'error', e.response?.data?.detail || 'Upload failed')
        }
      }
      await refresh()
      if (uploaded.length) {
        const last = uploaded[uploaded.length - 1]
        await setActive(last)
        send({ action: 'run_pipeline', filename: last })
      }
      return uploaded
    } finally {
      setLoading(false)
    }
  }, [refresh, send, setActive, updateQueue])

  const uploadFile = useCallback((file) => uploadFiles([file]), [uploadFiles])
  const clearQueue = useCallback(() => setQueue([]), [])

  const loadSample = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await api.post('/datasets/load-sample')
      await refresh()
      send({ action: 'run_pipeline', filename: data.dataset.filename })
      return data
    } finally {
      setLoading(false)
    }
  }, [refresh, send])

  const activeSummary = datasets.find((d) => d.filename === active) || null

  return (
    <DataContext.Provider value={{
      datasets, active, activeSummary, loading, refresh, uploadFile, uploadFiles, loadSample, setActive,
      queue, clearQueue,
    }}>
      {children}
    </DataContext.Provider>
  )
}

export function useData() {
  return useContext(DataContext)
}
