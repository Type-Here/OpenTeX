import client from './client'

export const listPermissions = (projectId) =>
  client.get(`/projects/${projectId}/permissions`).then(r => r.data)

export const assignPermission = (projectId, body) =>
  client.post(`/projects/${projectId}/permissions`, body).then(r => r.data)

export const revokePermission = (projectId, userId) =>
  client.delete(`/projects/${projectId}/permissions/${userId}`)
