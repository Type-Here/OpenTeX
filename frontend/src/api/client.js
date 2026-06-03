import axios from 'axios'

const client = axios.create()

client.interceptors.request.use((config) => {
  const stored = localStorage.getItem('opentex_user')
  if (stored) {
    const { user_id } = JSON.parse(stored)
    if (user_id) config.headers['X-User-Id'] = user_id
  }
  return config
})

export default client
