import client from './client'

export async function loginUser(email, password) {
  const res = await client.post('/auth/login', { email, password })
  return res.data
}

export async function registerUser({ email, password, first_name, last_name, department }) {
  const res = await client.post('/auth/register', { email, password, first_name, last_name, department })
  return res.data
}