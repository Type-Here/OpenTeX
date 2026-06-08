import client from './client'

export const listProjectFiles = (projectId) =>
  client.get(`/projects/${projectId}/files`).then(r => r.data)

export const updateFileContent = (fileId, content) =>
  client.put(`/files/${fileId}`, { content }).then(r => r.data)

export const createProjectFile = (projectId, filename, fileType) =>
  client.post(`/projects/${projectId}/files`, { filename, file_type: fileType }).then(r => r.data)

export const deleteFile = (fileId) =>
  client.delete(`/files/${fileId}`)

export const compileProject = (projectId) =>
  client.post(`/projects/${projectId}/compile`, null, {
    responseType: 'arraybuffer',
    validateStatus: () => true,
  })
