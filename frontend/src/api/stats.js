import client from './client'

export const getStats = (params) =>
  client.get('/stats/projects', { params }).then(r => r.data)

export const runBenchmarks = () =>
  client.get('/stats/benchmarks').then(r => r.data)
