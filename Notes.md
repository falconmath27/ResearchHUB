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
- **No DOI field yet:** the URL handles general web references. Add a normalized DOI field and a citation-parser integration once citation import becomes a priority.
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
