import { api } from './client'

export const getProfile = (filename) => api.get('/results/profile', { params: { filename } }).then((r) => r.data)
export const getPillars = (filename) => api.get('/results/pillars', { params: { filename } }).then((r) => r.data)
export const getHealth = (filename) => api.get('/results/health', { params: { filename } }).then((r) => r.data)
export const getIssues = (filename) => api.get('/results/issues', { params: { filename } }).then((r) => r.data)
export const getRanking = (filename) => api.get('/results/ranking', { params: { filename } }).then((r) => r.data)
