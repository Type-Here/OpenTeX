import client from './client'

export const getStats = (params) =>
  client.get('/stats/projects', { params }).then(r => r.data)

export const runBenchmarks = () =>
  client.get('/stats/benchmarks').then(r => r.data)

export const runCompileBenchmark = (runs = 5) =>
  client.get('/stats/compile-benchmark', { params: { runs } }).then(r => r.data)
