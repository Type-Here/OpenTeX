import client from './client'

export const getUsers = () => client.get('/users/').then(r => r.data)
export const getUserById = (id) => client.get(`/users/${id}`).then(r => r.data)
