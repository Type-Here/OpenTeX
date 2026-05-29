# OpenTeX - MongoDB Schema (Issue #1)

This document defines the five collections, their fields, and the minimum validation rules applied via `$jsonSchema`.

## Global modeling notes

- Embedding: small, stable metadata is embedded in `projects` (e.g., `tags`, `abstract`).
- Referencing: `files`, `permissions`, `activity_logs` store `ObjectId` references to related entities.
- Media storage: images and PDFs are stored on the filesystem; MongoDB stores only the `path`.
- Validation scope: required fields and core types are enforced; validators do not check referential integrity.

## Collection: `users`

Purpose: user profile and preferences.

Required fields:
- `email` (string, basic pattern)
- `first_name` (string)
- `last_name` (string)
- `department` (string)
- `created_at` (date)

Optional fields:
- `author_name` (string, used for authored-by when present)
- `preferences` (object)
- `orcid` (string)

## Collection: `projects`

Purpose: project metadata and ownership.

Required fields:
- `title` (string)
- `abstract` (string)
- `created_at` (date)
- `owner_id` (objectId -> users)

Optional fields:
- `tags` (array of strings)
- `updated_at` (date)

## Collection: `files`

Purpose: LaTeX source files and media references.

Required fields:
- `project_id` (objectId -> projects)
- `filename` (string)
- `file_type` (enum: `tex`, `bib`, `image`, `pdf`)
- `created_at` (date)

Conditional rules:
- `file_type` in `tex|bib` requires `content` (string)
- `file_type` in `image|pdf` requires `path` (string)

Optional fields:
- `content` (string)
- `path` (string)
- `updated_at` (date)

## Collection: `permissions`

Purpose: pivot collection for user-project roles.

Required fields:
- `user_id` (objectId -> users)
- `project_id` (objectId -> projects)
- `role` (enum: `Admin`, `Editor`, `Viewer`)
- `granted_at` (date)

## Collection: `activity_logs`

Purpose: audit trail for CRUD events and collaboration actions.

Required fields:
- `user_id` (objectId -> users)
- `project_id` (objectId -> projects)
- `action` (enum, see script)
- `timestamp` (date)

Optional fields:
- `metadata` (object)
