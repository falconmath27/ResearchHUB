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
