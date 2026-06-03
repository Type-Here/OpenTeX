import client from './client'

export const listProjects = (params) => client.get('/projects/', { params }).then(r => r.data)
export const getProject = (id) => client.get(`/projects/${id}`).then(r => r.data)
export const createProject = (body) => client.post('/projects/', body).then(r => r.data)
export const updateProject = (id, body) => client.put(`/projects/${id}`, body).then(r => r.data)
export const deleteProject = (id) => client.delete(`/projects/${id}`)
