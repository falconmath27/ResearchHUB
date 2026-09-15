# ResearchHub Notes

## Current Stack

- **Next.js + React:** The frontend renders the landing page and will later call the API.
- **FastAPI:** The Python web framework that receives HTTP requests and sends JSON responses.
- **Pydantic:** Validates incoming JSON against Python models before route code runs.
- **pytest:** Runs automated tests and reports whether behavior matches expectations.
- **httpx / TestClient:** Lets tests send simulated HTTP requests to FastAPI without starting a server.

## FastAPI In This Project

`backend/app/main.py` creates `app`, the FastAPI application.

- `@app.get("/health")` creates a read-only health-check endpoint.
- `@app.post("/projects", status_code=201)` creates a project endpoint.
- Route functions receive validated request data and return Python dictionaries. FastAPI converts those dictionaries to JSON.

HTTP status codes used so far:

- `200`: the request succeeded.
- `201`: a new resource was created.
- `422`: the request data was invalid.

## Pydantic Models

`backend/app/schemas.py` contains request shapes such as `ProjectCreate`.

- `ProjectCreate` defines which JSON fields `/projects` accepts: `title`, `summary`, and `field`.
- `Field(min_length=..., max_length=...)` applies validation limits.
- If validation fails, FastAPI returns `422` before the route function runs.

## Tests

Tests follow **Arrange, Act, Assert**:

1. Arrange the input data.
2. Act by calling a function or API route.
3. Assert the expected result.

`TestClient(app)` is a local stand-in for the frontend. For example, `client.post("/projects", json=payload)` tests the complete request-and-response path.

For a successful project request, the `payload` must meet every `ProjectCreate` rule. A short summary is useful in a separate rejection test that expects `422`.

## Project Detail Routes

`GET /projects/{project_id}` uses a path parameter. For example, `/projects/1` gives FastAPI the integer `1` as `project_id`.

- The route searches the in-memory `projects` list.
- A matching project is returned with status `200`.
- If there is no match, the route raises `HTTPException` with status `404`.
- `404 Not Found` means the requested resource does not exist.

## Updating Projects

`PUT /projects/{project_id}` updates an existing project.

- `PUT` is used when the client sends the replacement values for an existing resource.
- The path parameter identifies which project to update.
- `ProjectUpdate` validates the incoming replacement data.
- A successful update returns the changed `Project` with status `200`.
- Updating a missing project returns `404`.

The current project list is stored only in server memory. It is useful for learning request flow, but the data disappears when the server restarts. A database will replace this later.

## Deleting Projects

`DELETE /projects/{project_id}` removes an existing project.

- `DELETE` is the HTTP method for removing a resource.
- `enumerate(projects)` gives both an item's index and its value while looping through a list.
- `del projects[index]` removes the matching project from the in-memory list.
- `204 No Content` means deletion succeeded and the response has no body.
- Deleting an ID that does not exist returns `404 Not Found`.

## Test Isolation

Tests should not depend on the order in which pytest runs them. The project API temporarily uses shared in-memory state, so the tests reset that state before every test.

- `@pytest.fixture(autouse=True)` marks setup code that pytest runs automatically for every test.
- `projects.clear()` resets the in-memory list to an empty list.
- `create_test_project()` is a helper function used inside tests that need an existing project.
- Setup belongs inside the test that needs it. Code at the top level of a test file runs only once when Python imports the file, before the per-test reset fixture runs.

## Project Visibility And Tags

Projects can now describe both their discoverability and their research topics.

- `Literal["private", "public"]` restricts `visibility` to exactly those two allowed values.
- `tags: list[str]` stores zero or more text labels such as `"ai"` or `"databases"`.
- `Field(default_factory=list)` creates a fresh empty list for each new model. It avoids accidentally sharing one mutable list across projects.
- `ProjectCreate`, `ProjectUpdate`, and `Project` all include these fields so the API validates, stores, and returns the same data shape.
- A trailing comma after an assignment can create a tuple in Python. For example, `item.tags = payload.tags,` produces a tuple rather than a list.

## Query Parameters And Filtering

Query parameters are optional values added after `?` in a URL. They refine a request without changing its main route.

- `GET /projects` returns every project.
- `GET /projects?visibility=public` returns only public projects.
- The annotation `Literal["private", "public"] | None` makes the filter optional and restricts it to valid visibility values.
- FastAPI returns `422` automatically when a client supplies an invalid value, such as `visibility=team-only`.
- The list comprehension `[project for project in projects if ...]` builds a filtered list from the in-memory projects.

## Local Database Development

SQLite is a local file-based database. It is useful for development when a network cannot reach the production PostgreSQL database.

- `DATABASE_MODE=sqlite` is the default local mode in this project.
- SQLite stores development data in `backend/researchhub.db`, which Git ignores.
- SQLAlchemy uses the same engine interface for SQLite and PostgreSQL, so the application can later switch back to Supabase without rewriting every database call.
- The Supabase `DATABASE_URL` stays in `.env` for later; local mode simply does not use it.

## SQLAlchemy Models

SQLAlchemy maps Python classes to database tables.

- `Base` is the parent class for every database model in this project.
- `ProjectRecord` maps to the `projects` table through `__tablename__ = "projects"`.
- `Mapped[...]` describes the Python type stored in each database column.
- `mapped_column(...)` configures a column, including its primary-key and length rules.
- `JSON` stores the project `tags` list in SQLite.
- API models such as `ProjectCreate` validate HTTP data; database models such as `ProjectRecord` define persisted storage.

## Database Sessions

The SQLAlchemy engine and session have different responsibilities.

- The `engine` manages database connections.
- `SessionLocal` is a factory that creates a short-lived session for one unit of database work.
- A session can execute SQL, track ORM objects, and later commit changes as a transaction.
- `with SessionLocal() as session:` closes the session automatically after the work completes.

## Persistent Project CRUD

The project API now stores `ProjectRecord` rows in SQLite instead of a Python list.

- `session.add(record)` marks a new record for insertion.
- `session.commit()` saves inserts, updates, or deletes permanently in the database.
- `session.refresh(record)` reloads generated values such as the database ID after a commit.
- `session.get(ProjectRecord, project_id)` reads one row by primary key.
- `select(ProjectRecord)` builds a query for project rows; a `where(...)` clause applies the visibility filter in SQLite.
- The tag filter still runs in Python after the rows are loaded because tags are stored as JSON in this local prototype.
- The test fixture deletes database rows before every test, keeping tests independent while the local database file itself persists between application runs.

## Browser API Access (CORS)

The frontend runs at `http://localhost:3000` and FastAPI runs at `http://localhost:8000`. Browsers treat those as different origins.

- CORS is the browser security rule that controls whether one origin may call another.
- `CORSMiddleware` in FastAPI sends the permission headers needed by the browser.
- `allow_origins=["http://localhost:3000"]` allows the local Next.js app while avoiding a blanket allow-all rule.

## Creating Projects from the Frontend

The page at `/projects/new` is our first complete frontend-to-database feature.

- `useState` stores the current values of each form input and lets the page update as the user types.
- A form's `onSubmit` handler calls `event.preventDefault()` so the browser does not reload the page.
- `fetch` sends a `POST` request to FastAPI with a JSON request body. The `Content-Type` header tells FastAPI that the body is JSON.
- `response.ok` is true for successful HTTP responses. On success we clear the fields; on failure we display either FastAPI's validation message or a network-connection message.
- CSS Modules keep this route's styles scoped to `page.module.css`, avoiding accidental styling changes to the dashboard.

## Reading Projects in React

The `/projects` page fetches saved project data from `GET /projects` when the page first opens.

- `useEffect` runs a side effect after React displays the component. We use it for API calls, not for rendering calculations.
- The empty dependency list, `[]`, means this request runs once when the page is mounted.
- `useState<Project[]>([])` gives TypeScript the shape of API data and starts with an empty project list.
- The UI has separate states for loading, connection errors, no results, and fetched results so users always receive useful feedback.
- `projects.map(...)` turns each API object into a project card. React uses each database `id` as a stable `key`.

## Dynamic Project Routes

Project cards now link to `/projects/[projectId]`, which displays one project from `GET /projects/{id}`.

- `[projectId]` is a dynamic Next.js route segment. For example, `/projects/4` makes `projectId` equal to `"4"`.
- `useParams` reads dynamic route values inside a client component.
- The detail page's effect depends on `projectId`, so it requests fresh data if the route changes without unmounting the component.
- A `404` response is handled separately to distinguish an unknown project from a failed API connection.

## Updating and Deleting from React

The project detail page can now update or delete the project it displays.

- `PUT /projects/{id}` replaces the editable project fields. The frontend preserves `tags` and `visibility` while editing the basic fields.
- `FormData` reads values from a submitted form without making a separate state value for every edit input.
- `DELETE /projects/{id}` removes the project. `confirm(...)` gives the user a final browser prompt before this irreversible action.
- `useRouter().push("/projects")` navigates back to the project list after a successful deletion.

## Tags, Visibility, and Filters

The frontend now exposes the project metadata already supported by the API.

- Comma-separated tag text is converted into a string array with `split`, `trim`, and `filter(Boolean)` before it is sent as JSON.
- A `select` element limits visibility to the two backend-supported values: `private` and `public`.
- The project list builds `URLSearchParams` for optional `visibility` and exact `tag` filters, then calls `GET /projects?visibility=...&tag=...`.
- The filter state is in the `useEffect` dependency list, so the project request reruns whenever a filter changes.

## User Database Model

`UserRecord` is the SQLAlchemy model for an application user. It defines the future `users` database table.

- `email` is marked `unique=True`, so the database rejects two users registering with the same email address.
- `password_hash` is deliberately separate from a password input. We will hash the password before saving it, so the database never stores a readable password.
- The user table has no project relationship yet. The next ownership step will add a user reference to each project.

## Registration Schemas

`UserCreate` validates data received when somebody registers, while `User` is the safe user data that the API will return.

- `EmailStr` validates the email format. It needs the `email-validator` package because Pydantic delegates email validation to that library.
- The registration request includes a plain `password` temporarily in memory, but the response schema deliberately omits it.
- `pytest.raises(ValidationError)` verifies that Pydantic rejects invalid inputs, such as a password shorter than eight characters.

## Password Hashing

Before registration data is saved, the application converts a password into a one-way Argon2 hash.

- `hash_password` produces the protected string that is saved in `UserRecord.password_hash`.
- `verify_password` checks a later password attempt against that saved hash without recovering the original password.
- The hashing test checks both the successful password and a wrong password, and confirms the hash is not equal to the readable password.

## User Registration Endpoint

`POST /auth/register` combines validation, security, and persistence to create a safe user account.

- The route uses `select(UserRecord).where(...)` before inserting, so it can return `409 Conflict` for an already-registered email.
- The database receives `hash_password(user.password)`, never `user.password` itself.
- `response_model=User` ensures the password and `password_hash` are excluded from the API response.
- The test fixture clears the `users` table as well as `projects`, which keeps registration tests independent.

## Login and JWT Access Tokens

`POST /auth/login` checks a registered user's password and returns a signed JSON Web Token (JWT).

- The route returns `401 Unauthorized` for either an unknown email or a wrong password. Using one message avoids revealing whether an email address is registered.
- `create_access_token` stores the user ID in the JWT `sub` (subject) claim and adds an expiration time with `exp`.
- The JWT is signed with `JWT_SECRET_KEY`. The development fallback works locally, but a production deployment must set a long, private `JWT_SECRET_KEY` environment variable.
- The API returns `token_type="bearer"`, which tells clients to send it later as `Authorization: Bearer <token>`.
- Email addresses are normalized to lowercase when accounts are registered and when users sign in. The database lookup also uses `lower(email)` so existing mixed-case records remain reachable. This avoids treating the same email as different accounts purely because of casing.

## Protected Current-User Route

`GET /auth/me` is the first protected endpoint. It returns the account represented by a valid bearer token.

- `HTTPBearer` reads the `Authorization: Bearer <token>` header and provides the token string to the route.
- `jwt.decode` verifies the JWT signature and expiry, then reads the `sub` user ID claim.
- The API checks that the user still exists in the database, because a valid token should not grant access after the account is removed.
- Invalid, expired, malformed, or userless tokens return `401 Unauthorized` rather than user data.

## Database Migrations and Project Membership

Alembic now manages changes to the database schema instead of having FastAPI create tables automatically at startup.

- `alembic upgrade head` applies every migration not yet recorded in the database's `alembic_version` table.
- The baseline migration represents the existing `users` and `projects` tables. We stamp the existing SQLite database at that revision, then apply the membership migration without rebuilding or deleting data.
- `ProjectMemberRecord` is the join table between users and projects. One project can have many members and one user can join many projects.
- The unique constraint on `(project_id, user_id)` prevents the same user from being added twice to one project.
- `role` is stored per membership, allowing multiple users to have the `owner` role, while other members can later receive `editor` or `viewer` roles.

## Project Ownership and Access Control

Projects now belong to authenticated members rather than being open to every API caller.

- Creating a project requires a bearer token and automatically creates an `owner` membership for that user.
- Project listing joins `projects` with `project_members`, so a user sees only projects where they are a member.
- Missing membership returns `404 Project not found`, which avoids revealing that a private project exists.
- Owners and editors may update a project. Only owners may delete one.
- The React sign-in page stores the token in browser local storage, and `apiFetch` automatically sends it on project API requests.

## Adding Project Members

Project owners can now add registered users to a project with a role.

- `ProjectMemberCreate` accepts the target user's email and one allowed role: `owner`, `editor`, or `viewer`.
- `POST /projects/{project_id}/members` first checks that the caller is an owner, then looks up the target user by email.
- The existing membership check returns `409 Conflict` instead of creating duplicate membership rows.
- A `ProjectMember` response combines safe user information with their role, while keeping password data private.
- The authorization test proves that a user who is not an owner cannot invite members.

## Managing Team Roles

The project membership API now supports reading, updating, and removing members.

- Any project member can call `GET /projects/{project_id}/members` to see the team and each member's role.
- Only owners can change a role with `PUT /projects/{project_id}/members/{user_id}` or remove a member with `DELETE`.
- A project must always retain at least one owner. Removing or demoting the final owner returns `409 Conflict`.
- The member list query joins `project_members` to `users`, which combines the membership role with safe user profile fields.

## Project Notes: System Design

Research notes are a separate resource under a project: `notes` has `project_id`, `author_id`, title, content, and audit timestamps.

- **Aggregate boundary:** routes use `/projects/{project_id}/notes`. The project is the authorization boundary, so every note request first proves the caller is a project member.
- **Authorization policy:** viewers can read; owners and editors can manage every note; an author can also edit or delete their own note. This matches a collaborative research workflow without granting every reader write access.
- **Data integrity:** foreign keys connect each note to a project and author. Deleting a project cascades to its notes, preventing orphan records.
- **Auditability:** `created_at` and `updated_at` record when a note was created and last changed. This is not full version history yet; it is the first audit layer.
- **API contract:** Pydantic limits titles to 200 characters and note content to 10,000 characters. Validation happens at the API boundary before the database work begins.

Interview answer: “I modelled notes as project-scoped resources, kept author identity for accountability, and enforced permissions at the API boundary. That avoids relying on the frontend for security and keeps the model ready for later version history.”

## Note Version History: Notion-Style Restore Safety

The notes workspace now uses a Notion-style page-history pattern: every saved state is preserved in a readable timeline, and restoring an earlier version creates a new latest version rather than rewriting history.

- **Immutable append-only revisions:** creating a note stores Version 1. Every edit writes another `note_versions` row in the same transaction as the note update. Version rows are never edited in place.
- **Safe restore:** `POST /projects/{project_id}/notes/{note_id}/versions/{version_id}/restore` copies an older title and content into the live note, then records that restored state as the next version. For example, restoring Version 1 after Version 2 creates Version 3. Version 2 remains available.
- **Authorization:** every project member may inspect note history. The same author/editor/owner policy used for editing a note protects restore actions; viewers cannot alter a project note by calling the API directly.
- **Audit identity:** each revision stores `edited_by_id`, and the version-list endpoint joins it to `users` to return an editor name. The foreign key uses `SET NULL`, so historical content remains readable if a former member’s user account is removed.
- **Data integrity:** `UNIQUE(note_id, version)` prevents duplicate version numbers for a note. The `(project_id, note_id)` index supports the normal history-timeline query without scanning every project's revisions.
- **Transaction boundary:** the note update and its version snapshot commit together. A failed database operation creates neither a changed live note nor a false history entry.

### Tradeoffs and Future Improvements

- **Storage growth:** complete snapshots are simple to restore and perfect for our 10,000-character note limit, but large documents would eventually need version retention rules, compressed snapshots, or content-diff storage.
- **Concurrent edits:** the current MVP assigns the next version number in application code. Two simultaneous writers could race in a high-traffic deployment; the database uniqueness rule detects the conflict, and production should add optimistic locking or a transaction retry.
- **No character-level collaboration:** this is version history, not Google Docs-style live co-editing. Real-time cursors and conflict-free merging require WebSockets, operational transforms or CRDTs, presence state, and a much more complex editor.

Interview answer: “I used an append-only version ledger for research notes, inspired by page-history workflows. Restores are non-destructive: they become a new version, which keeps the full reasoning trail. I put authorization and snapshot creation in the API transaction, so the frontend cannot bypass the audit trail.”

## Research Tasks: System Design

Tasks are also project-scoped records, but they add workflow state and optional assignment.

- **State machine:** the only accepted statuses are `backlog`, `in_progress`, `in_review`, and `done`. The `TaskStatus` type makes invalid statuses fail validation instead of entering the database.
- **Assignment boundary:** `assignee_id` is optional, but if supplied the API verifies that the user is already a member of the same project. This prevents assigning internal work to an unrelated account.
- **Role-based access control:** all members can read the board. Owners and editors can create, update, assign, and delete tasks. Viewers have read-only access.
- **Filtering:** `GET /projects/{project_id}/tasks?status=...` filters in the database, rather than loading every task and filtering in the browser.
- **Independent scaling:** notes and tasks have separate tables and endpoints. This avoids a single overloaded “content” table and lets us index, paginate, or version each resource differently later.

Interview answer: “Tasks are a small state machine scoped to a project. I kept authorization, assignment validation, and filtering on the server so the client is only a user interface, not a security boundary.”

## Integrity and Tradeoffs

- **Atomic project creation:** a project and its creator membership are created in one transaction. We use `session.flush()` to obtain the project ID, add the owner membership, then call one `commit()`. The earlier two-commit approach could have left an ownerless project if the second operation failed.
- **SQLite foreign keys:** SQLite does not enforce foreign keys by default. The database connection now executes `PRAGMA foreign_keys=ON`, so cascade and reference rules behave in local development as intended.
- **Join table:** `project_members` is a many-to-many association with role data. It solves the “multiple owners” requirement without adding a fragile comma-separated owner list to `projects`.
- **Known limitation:** the final-owner check is application-level. Under heavy concurrent requests, two owners could theoretically both try to remove themselves. A production system should add transaction locking or a database trigger for that invariant.
- **Known limitation:** the browser currently stores JWTs in local storage for learning simplicity. A production deployment should use short-lived access tokens with refresh tokens in secure, HTTP-only cookies to reduce XSS exposure.

## Test Database Isolation

Automated tests must never point at the same database as the running application. Our test fixture intentionally deletes rows before every test to make the cases independent; when it used `researchhub.db`, that useful test behavior also erased real local accounts and projects.

- `tests/conftest.py` now sets `SQLITE_DATABASE_PATH` to `backend/test_researchhub.db` before the application modules are imported by pytest.
- The application config reads that environment variable only for SQLite. The normal server continues to use `backend/researchhub.db`.
- The temporary test database is deleted at the beginning and end of a pytest session and is ignored by Git.

Interview answer: “I isolated test state from development state using an environment-configured database path. Tests can freely reset their database for deterministic results, while the developer's real local data remains intact. This is the local version of using a separate test database or ephemeral container in CI.”

## Project Discussion: System Design

Project discussion is a lightweight, project-scoped message feed inspired by Linear-style project updates and Slack-style chronological conversation.

- **Data model:** `messages` stores `project_id`, `author_id`, message `content`, and `created_at`. The author and project foreign keys provide accountability and prevent orphan records when a project or account is removed.
- **Authorization boundary:** both `GET /projects/{project_id}/messages` and `POST /projects/{project_id}/messages` require project membership. Non-members receive `404`, so private-project existence is not disclosed.
- **Collaboration policy:** every project role, including `viewer`, can read and post messages. Unlike notes and tasks, discussion is a communication surface, so read-only project access should not prevent a collaborator from raising a question or reporting a blocker.
- **Query design:** messages are read in chronological order. The `(project_id, created_at)` index supports the most common access pattern: loading one project’s conversation efficiently as it grows.
- **Author projection:** the message response includes `author_name`, retrieved with a join to `users`. This avoids an extra frontend request for every message, which would otherwise create the N+1 query problem.
- **Input validation:** `MessageCreate` strips whitespace and rejects blank content at the API boundary. This avoids storing empty messages even if a client bypasses browser form validation.

### Why This MVP Is Not Real-Time or Threaded

- **No WebSockets yet:** regular request/response APIs are simpler to test and deploy. Real-time delivery introduces persistent connections, connection recovery, event ordering, authorization on socket upgrade, and horizontal-scaling concerns.
- **No replies yet:** a `parent_message_id` field would support threads, but it introduces recursive queries, thread ordering, unread-state design, and more UI complexity. It should be added only after the flat discussion feed proves useful.
- **Append-only messages:** messages are not editable or deletable in version one. That protects conversation context and keeps the first audit trail simple. Future moderation should use explicit delete/audit events rather than silently rewriting history.

Interview answer: “I modelled discussion as a project-scoped append-only feed. Membership is checked on the server for reads and writes, and I join author data in the list query to avoid N+1 frontend calls. I deliberately deferred WebSockets and threads because they add operational complexity before the core collaboration workflow is validated.”

## Live Frontend Integration

The original home screen was a static Canvas prototype with hard-coded papers, tasks, and chat text. It looked like a product, but it was disconnected from the FastAPI database, so it could not demonstrate the implemented features.

- The root route now fetches the authenticated user's real projects from `GET /projects` through `apiFetch`.
- Every project card provides direct navigation to its overview, notes, tasks, and discussion workspace.
- The dashboard distinguishes loading, unauthenticated, empty, and loaded states instead of showing fake data.
- This follows the “single source of truth” principle: project data comes from the API/database, not from a separate hard-coded frontend array.

Interview answer: “I replaced the static prototype dashboard because a frontend that displays mock state can drift from the backend. The homepage now consumes the same protected project API as the rest of the application, so the UI reflects persisted data and authorization rules.”

## Research Sources: System Design

The source library stores reference metadata separately from uploaded files. A `sources` record belongs to one project and records a title, authors or organization, publication year, controlled source type, optional external URL, creator, and audit timestamps.

- **Metadata before files:** a paper, website, dataset, or report can be useful without a local attachment. Separating source records from files lets the project catalogue external links now and attach a PDF or dataset later without duplicating citation information.
- **Controlled vocabulary:** source type is limited to `article`, `book`, `dataset`, `report`, `website`, or `other`. This prevents inconsistent values such as `Paper`, `paper`, and `journal article`, and supports reliable filtering.
- **Authorization:** every project member can read sources; only owners and editors can create, update, or delete them. The backend, not the React page, enforces this rule.
- **Indexing:** the `(project_id, source_type)` index supports the main library query: retrieve one project’s sources, optionally filtered by type.
- **Input safety:** URLs are validated as `HttpUrl` at the API boundary. The frontend renders them as an external link with `rel="noreferrer"`, which prevents the destination page from receiving the ResearchHub page as referrer information.
- **Cascades:** deleting a project removes its source metadata through the project foreign key, avoiding orphan references.

### Tradeoffs and Future Improvements

- **Authors are a single text field:** this is fast for a research MVP and handles organizations, but it does not support author-specific search or normalized identities. A future `source_authors` table would support ordered authors, ORCID IDs, and better citation export.
- **No automatic metadata import yet:** DOI values now identify publications reliably, but users still enter titles, authors, and years themselves. A future Crossref or OpenAlex integration could resolve a DOI into citation metadata while retaining a review step before saving external data.
- **No file record yet:** the following upload feature should create an attachment table that points to `source_id`, rather than putting filesystem details directly on the source row.

Interview answer: “I treated sources as project-scoped metadata independent from file storage. That keeps citations reusable, supports external links and datasets, and gives us a clean attachment boundary for the next feature. I used controlled source types and a composite index because filtering the source library is a primary access pattern.”

## Source Attachments: Zotero-Inspired Evidence Management

The source library now follows a Zotero-inspired model: a source is the citation and metadata record, while an attachment is a separate file record linked to that source. This lets one reference have several supporting files, such as a PDF, cleaned CSV, or analysis notes, without duplicating the citation each time.

- **Separate resources:** `attachments` has its own table with `project_id`, optional `source_id`, uploader ID, original filename, private stored filename, MIME type, file size, and creation time. A source can exist without a local file, which is important for websites and externally hosted datasets.
- **Many-to-one relationship:** several attachments can point to one `source_id`. The attachment is also project-scoped, so access checks never depend only on a numeric attachment ID.
- **Retention policy:** deleting a source sets `source_id` to `NULL` rather than deleting its attachments. The file moves to the visible Project files section, which avoids accidentally losing evidence because a citation record was removed.
- **Role-based access control:** all project members can list and download attachments. Only owners and editors can upload or delete them. The FastAPI routes enforce this on the server; hiding a button in React is only a usability improvement, not security.
- **Authenticated download:** downloads pass through `GET /projects/{project_id}/attachments/{attachment_id}/download`, which checks membership before returning `FileResponse`. The React page downloads with `apiFetch`, so the bearer token is included. A normal public `<a>` URL would not attach that authorization header.
- **Safe names:** the original filename is only for display and download. The actual file is stored as a generated UUID plus its allowed extension. This prevents two `paper.pdf` uploads from overwriting each other and avoids using a user-controlled path as a server filename.
- **Upload controls:** permitted extensions are PDF, CSV, TSV, TXT, DOCX, XLSX, and JSON. Files are streamed in 1 MB chunks and stopped at 20 MB, instead of reading the full upload into memory at once. This limits accidental large uploads and reduces memory pressure.
- **Tests:** attachment tests cover upload, source linkage, list, protected download, deletion, rejected extensions, and viewer denial. The browser flow is backed by the same protected API rather than a mock upload widget.

### Storage Design and Production Tradeoffs

- **Local development:** files are stored under `backend/uploads/`, which is ignored by Git. This makes the feature work without an external account or network dependency.
- **Production evolution:** a multi-instance deployment must move binary files to object storage such as Amazon S3, Cloudflare R2, or Supabase Storage. Local disk is tied to one server and can be lost during a redeploy; shared object storage is durable and accessible from every API instance.
- **Database/file consistency:** SQLAlchemy can roll back database records, but it cannot include a local filesystem write in the same database transaction. The implementation deletes the new file if creating the database record fails, and deletes the file after its row is removed. This is practical for an MVP, but production should use object-store lifecycle rules and an outbox/cleanup job to handle crashes between the two operations.
- **Security boundary:** an extension allow-list is a first filter, not a complete malware defense. A production system should verify file signatures (magic bytes), scan uploads for malware, enforce quotas by user/project, and store files in a private bucket with short-lived signed download URLs.
- **Indexing:** the attachment migration adds an index on `(project_id, source_id)`, matching the common query of loading files for one source in one project.

Interview answer: “I kept citation metadata and binary evidence separate, similar to a reference manager. Attachments are project-scoped and authorization is checked before every list or download. For the MVP I stream allowed files to local storage with generated names and a size cap; in production I would replace local disk with private object storage, malware scanning, signed URLs, and a cleanup workflow for database-to-object-store consistency.”

## Source Search and DOI Identity

The source library now supports project-scoped text search and normalized Digital Object Identifiers (DOIs). This turns the library from a list users must scan manually into a searchable research catalogue and gives academic publications a stable identity independent of a publisher URL.

- **Composable search:** `GET /projects/{project_id}/sources?q=...&source_type=...` searches source titles, authors or organizations, and DOIs without case sensitivity. The text query and controlled source-type filter can be used separately or together. Filtering remains in SQL, so the API does not load a project's full source library and filter it in Python.
- **Authorization boundary:** search uses the existing protected source-list endpoint. The API verifies project membership before running the query, so search cannot be used to discover metadata from a private project.
- **Literal substring behavior:** `%`, `_`, and the escape character are escaped before building the SQL `LIKE` pattern. Users therefore search for literal text instead of accidentally supplying SQL wildcard behavior. Bound SQLAlchemy parameters continue to protect the query from SQL injection.
- **Canonical DOI storage:** the API accepts a bare DOI, a `doi:` value, or `doi.org` and legacy `dx.doi.org` URLs. It trims the input, removes the resolver prefix, and lowercases the result before persistence. For example, `https://doi.org/10.1000/Example` becomes `10.1000/example`.
- **Boundary validation:** DOI validation requires the standard `10.` registrant prefix, four to nine registrant digits, a slash, and a non-whitespace suffix. Blank input becomes `NULL`, keeping DOI optional for websites, local reports, and other material without one.
- **Project-scoped uniqueness:** a database unique constraint on `(project_id, doi)` prevents the same publication from being catalogued twice in one project while allowing separate projects to maintain independent libraries. SQLite and PostgreSQL both permit multiple `NULL` DOI values, so sources without a DOI remain valid.
- **Concurrency safety:** request validation gives users early feedback, while the database constraint is the final authority if two requests try to insert the same DOI concurrently. The API rolls back the failed transaction and returns `409 Conflict` with a useful duplicate message.
- **Responsive frontend search:** the source page waits 300 milliseconds after typing before requesting results. This debounce keeps typing responsive and avoids sending one API request for every keystroke. The page includes distinct searching, no-library-data, no-search-results, validation-error, and duplicate-DOI states.
- **Resolvable DOI links:** stored canonical values are displayed as links to `https://doi.org/{doi}`. A normal source URL remains separate because it may point to a dataset, project page, preprint, or supplementary material rather than the DOI resolver.

### System-Design Tradeoffs, Risks, and Mitigations

- **Substring search before full-text search:** `ILIKE '%term%'` is simple, portable across the local SQLite setup and production PostgreSQL, and sufficient for the current project-sized dataset. A normal B-tree index cannot efficiently serve a leading-wildcard query, so very large libraries should move to PostgreSQL full-text search or trigram indexes, ranked results, and pagination.
- **Normalization versus exact representation:** lowercasing and removing resolver prefixes makes equality checks and duplicate prevention predictable. ResearchHub preserves the DOI identity rather than the user's original formatting; this is intentional because display links can be reconstructed from the canonical value.
- **Practical validation rather than registry verification:** the API checks DOI syntax but does not make a network call to prove that the DOI currently resolves. This keeps source creation fast and available offline. Future metadata import can verify resolution asynchronously and show a warning without blocking users from recording valid-but-temporarily-unavailable research.
- **Database constraint over application-only checks:** checking duplicates only in route code would have a race condition. The composite unique constraint guarantees the invariant under concurrent writes; the API converts the expected integrity failure into a domain-level `409` response.
- **Search request races:** React cancels the effect's state update when the filter or debounced query changes. A slower response for an older query therefore cannot overwrite newer visible results, even though the underlying HTTP request may still finish.

Interview answer: “I added normalized, project-scoped DOI identity and composable source search. DOI normalization makes duplicate detection deterministic, while a composite database constraint protects the invariant under concurrency. Search runs behind the existing membership boundary and uses escaped, parameterized substring matching for a portable MVP. At larger scale I would move PostgreSQL to trigram or full-text indexes, ranked results, and pagination.”

Migration `20260915_0008` adds the nullable DOI column and `(project_id, doi)` unique constraint. Source-specific coverage includes DOI normalization, invalid DOI rejection, duplicate conflict handling, and search across title, author, and DOI combined with source-type filtering.

## Authentication UX Reliability

The authentication screen now distinguishes credential, validation, and connectivity failures instead of making a failed submission look like an inactive button.

- Switching between Register and Sign in clears an error from the previous mode, preventing stale feedback from appearing to belong to the new form.
- FastAPI validation details are converted into readable text instead of rendering as an unhelpful object value.
- A network failure explicitly tells the developer to check the backend on port 8000, while incorrect credentials retain the safer generic authentication response.
- The frontend API origin can be overridden with `NEXT_PUBLIC_API_BASE_URL`; the localhost default remains zero-configuration for development.
- FastAPI accepts the two equivalent local browser origins, `localhost:3000` and `127.0.0.1:3000`. Production should replace these development origins with the deployed frontend origin rather than allowing every origin.
- Mode buttons expose `aria-pressed`, and authentication inputs include appropriate autocomplete metadata for clearer assistive-technology and password-manager behavior.

Interview answer: “I treated authentication errors as part of the API contract, not just styling. The UI separates server validation, rejected credentials, and an unreachable API, clears stale state when modes change, and keeps CORS narrowly allow-listed to known development origins.”

## Password Reset and Manual Account Recovery

ResearchHub now separates two account-loss scenarios instead of treating them as the same problem. A user who knows their registered email can reset their password with a short-lived token. A user who cannot remember or access that email can create a manual support case, but the public recovery flow never reveals an account email or grants access automatically.

### Password Reset Workflow

- `POST /auth/password-reset/request` always returns `202 Accepted` and the same message for registered and unregistered emails. This prevents attackers from using the endpoint to enumerate ResearchHub accounts.
- The backend generates reset tokens with a cryptographically secure random generator. Only a SHA-256 hash is stored in `password_reset_tokens`; possession of the database alone does not reveal a usable reset link.
- Reset tokens expire after 30 minutes and are single-use. Requesting another token invalidates previous unused tokens for that account, reducing the window created by old emails or copied links.
- The reset page reads the token once and removes it from the visible URL and browser history. This reduces accidental disclosure through copied URLs, screenshots, analytics, or referrer headers.
- `POST /auth/password-reset/confirm` changes the Argon2 password hash and consumes every outstanding token for that user in the same database transaction. Invalid, expired, or previously used tokens receive one generic failure response.
- Requests are limited to three token issuances per email fingerprint per hour. The fingerprint is an HMAC made with the server secret, so unknown email addresses do not need to be stored in plaintext merely to enforce rate limits. Rate-limited requests still receive the same public response.
- In local `development` delivery mode, the API returns a reset URL so the complete flow can be demonstrated without an email account. Even unknown emails receive a plausible but unusable development token, preserving response-shape privacy.
- `PASSWORD_RESET_DELIVERY_MODE=email` removes the token from the response and fails closed. A production deployment must connect a transactional email provider before enabling this mode; reset tokens must never be logged or returned to a production browser.

### Session Revocation

Each user now has a `token_version`. JWTs carry the version that existed when the session was created, and protected routes compare it with the current database value.

- A successful password reset increments `token_version`, immediately invalidating every older access token for that account.
- This adds one user lookup to authenticated requests, which the application already performed to verify that the user still exists.
- The design revokes all sessions rather than tracking individual devices. Device-level session management would require server-side session records or refresh-token families and is a future improvement.

### Manual Support-Assisted Recovery

- `POST /auth/account-recovery` accepts the user's name, a reachable contact email, an optional remembered account email, and a minimum amount of context for manual verification.
- The response contains a high-entropy reference code such as `RH-...`. The requester can check case status with the reference code plus the contact email; knowing only a reference code is insufficient.
- Cases begin in `pending` and support can move them through `in_review`, `resolved`, or `rejected`. The current MVP deliberately has no public endpoint that changes status or account credentials.
- Support must verify ownership using evidence appropriate to the organization, such as previously known project membership, institutional identity, or a verified secondary channel. A matching name or remembered email alone must never be treated as proof.
- Manual recovery records contain personal information. Production needs a restricted support console, audit logs for operator actions, encrypted storage where appropriate, retention/deletion rules, and access limited to trained support staff. Until that operator boundary exists, cases remain safe pending records rather than automatic recovery grants.

### Tradeoffs, Risks, and Mitigations

- **Email delivery is an adapter boundary:** secure token creation and consumption are implemented, but ResearchHub intentionally does not fake production delivery. A provider such as Amazon SES, Postmark, or Resend should be integrated through a background job with retry and delivery-event handling.
- **Database-backed rate limiting:** it works across multiple API instances and survives restarts, unlike an in-memory counter. Old attempt rows need periodic retention cleanup; an API gateway or Redis limiter should additionally enforce per-IP and global abuse controls.
- **Hashing reset tokens:** random high-entropy tokens do not require slow password hashing, so SHA-256 is appropriate and efficient. Passwords still use Argon2 because human-created passwords have far less entropy and need expensive hashing.
- **Manual recovery avoids unsafe automation:** account recovery is slower for a user who lost their email, but it avoids an automated flow that could disclose private accounts or let weak biographical guesses take over a workspace.
- **Reference-code status lookup:** requiring both the random code and contact email provides practical case tracking. Production should also expire or archive old cases and avoid putting sensitive case details in the status response.

Interview answer: “I split password reset from identity recovery. Password reset uses enumeration-safe responses, rate-limited requests, hashed single-use tokens, expiration, and a token-version change that revokes old JWTs. Losing the email becomes a manual support case with a high-entropy reference code; it never automatically reveals or transfers the account. The email provider and restricted support console remain explicit production boundaries rather than insecure shortcuts.”

Migration `20260915_0009` adds token-version session revocation, reset-attempt fingerprints, password-reset tokens, and manual recovery requests. The backend suite has 62 passing tests. Targeted authentication lint and the optimized frontend build pass, including the new `/auth/reset` route.

## AI Source Analysis: Durable Job Contract and Text Extraction

ResearchHub now has the provider-independent foundation for AI source analysis. Owners and editors can prepare an attached PDF or TXT file from the source library, while every project member can inspect job status and extraction results. This slice deliberately labels successful output as **AI-ready extraction**: no model is connected yet, so the application does not misrepresent deterministic document processing as an AI-generated summary.

### Explicit Job State Machine

`analysis_jobs` stores each request with one of four states:

1. `queued`: the API accepted and persisted the request.
2. `processing`: one worker claimed the job and started extracting text.
3. `completed`: bounded, usable text and document metadata were persisted successfully.
4. `failed`: extraction stopped safely with a stable error code and a user-safe message.

- The job is committed before background work begins. The HTTP request can therefore return `202 Accepted` with a job ID instead of keeping a slow extraction operation inside the request transaction.
- `started_at` and `completed_at` make queue delay and processing duration measurable. `attempt`, `parent_job_id`, and immutable job rows preserve retry history rather than overwriting the original failure.
- Results include file type, PDF page count when applicable, character count, word count, truncation state, extracted text, and a 1,000-character UI preview.
- The frontend polls every 1.5 seconds only while at least one job is queued or processing. Polling stops automatically for terminal states, avoiding permanent background traffic.

### Concurrency-Safe Deduplication and Retry

- An active job has an `active_key` derived from its attachment. A unique constraint on `(project_id, active_key)` permits only one queued or processing job per attachment in a project.
- The route first reuses an existing active job for normal idempotency. The database constraint remains the final authority when simultaneous requests race; the losing transaction rolls back and returns the winning job.
- Terminal jobs clear `active_key`, allowing a deliberate new extraction. Failed jobs can be retried through a dedicated endpoint, which creates a new attempt linked to the failed parent.
- Only a `failed` job can use the retry endpoint. This prevents ambiguous retries of running or already successful work.

### Extraction Safety

- TXT files must use UTF-8 (including UTF-8 with a byte-order mark). Invalid encodings fail with a stable `invalid_text_encoding` code rather than silently corrupting evidence.
- PDFs are parsed with `pypdf`. Encrypted PDFs, unreadable PDFs, files without useful embedded text, and PDFs over 200 pages fail with specific safe errors.
- Extracted content is capped at 500,000 characters. Counts describe the full cleaned text, while the stored extraction is bounded and marked `truncated` when the cap applies.
- The processor removes null characters and normalizes excessive whitespace before measuring and storing text. It never returns Python exceptions, filesystem paths, database details, or stack traces to the browser.
- Unexpected failures are logged server-side with the job ID, while users receive the generic `internal_error` message. Expected document failures use stable codes that a future UI or support system can translate.

### Authorization and Data Boundaries

- Owners and editors can start and retry analysis because processing creates project data and may later consume paid model capacity. Viewers can inspect job state and results but cannot initiate work.
- Every route validates both project membership and the attachment's project scope. Numeric attachment or job IDs cannot cross a project boundary.
- Deleting an attachment cascades to its analysis history. This matches the current evidence-retention decision: extracted document text should not survive deletion of the private source file from which it came.
- Only PDF and TXT attachments are accepted in this first slice. Other upload types remain downloadable but receive `422` if submitted for analysis.

### Tradeoffs, Risks, and Production Evolution

- **FastAPI background tasks are an MVP executor, not a durable queue:** they provide the asynchronous API contract without operating Redis or a worker service, but a server crash can strand a job in `queued` or `processing`. Production should use Celery, Dramatiq, RQ, or a managed queue, with leases, heartbeat timestamps, retry backoff, a dead-letter queue, and a watchdog that recovers abandoned jobs.
- **Database state is the source of truth:** frontend polling can disconnect without losing the job. A later WebSocket or server-sent-events channel can reduce polling latency without changing the job contract.
- **Full extracted text is stored per completed attempt:** this makes the next model stage reproducible and easy to inspect, but repeat jobs increase storage. Production should deduplicate extraction by attachment content hash, encrypt sensitive text at rest, define retention, and store large text or chunks outside the transactional row.
- **No OCR yet:** `pypdf` extracts embedded text but scanned-image PDFs will produce `no_extractable_text`. OCR needs a sandboxed, resource-limited service and language configuration rather than being hidden inside the API process.
- **Parser isolation:** PDF parsers process untrusted files. The 20 MB upload cap and 200-page extraction cap limit resource use, but production should isolate parsing in a constrained worker/container, enforce CPU and memory limits, keep dependencies patched, and malware-scan uploads.
- **Prompt injection is the next-stage threat:** extracted papers are untrusted data. When a model provider is connected, document instructions must never override the system task, request secrets, invoke tools, or trigger external actions. Outputs need provenance and citations back to source chunks.
- **No AI claims yet:** `completed` currently means extraction completed, not that an LLM produced findings. The next migration can add an analysis stage or job type without changing the queue, authorization, retry, or observability foundations.

Interview answer: “I separated the analysis request from execution with a persisted four-state job model. I used a nullable active-key uniqueness constraint to make job creation idempotent under concurrency, preserved retries as linked attempts, and exposed only stable failure codes. The MVP executor is FastAPI BackgroundTasks, but the database contract is designed to move to a durable worker queue. Text extraction is bounded, project-authorized, and explicitly presented as AI-ready rather than fabricated AI output.”

Migration `20260915_0010` creates the analysis job ledger and its project/attachment and project/status indexes. The backend suite has 67 passing tests, including successful TXT and generated-PDF extraction, safe extraction failure, retry lineage, active-job reuse, unsupported-file rejection, and viewer authorization. Full frontend lint, TypeScript checking, and the optimized production build pass.
