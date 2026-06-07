import axios from 'axios'

const client = axios.create()

client.interceptors.request.use((config) => {
  const stored = localStorage.getItem('opentex_user')
  if (stored) {
    const { token } = JSON.parse(stored)
    if (token) config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

export default client