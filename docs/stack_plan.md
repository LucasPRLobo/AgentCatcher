# Tech Stack

## Honeypot Stack

### API

FastAPI. I already have experience with it and am familiar with programming with it.

- Log every request in a pure ASGI middleware that wraps the whole app, not `BaseHTTPMiddleware` or per-route logging. It sees 404s and requests that match no route (e.g. `/.env` probes), and it can capture request bodies without consuming them.
- Stamp the arrival time with `time.time_ns()` when the middleware first sees the request, not inside the handler.

### Loging and DB

For now we will only be logging requests for analysis. Therefore, we can use a relational database (SQL). We could consider later on if we will look at not just agent requests to use No-SQL DBs to store unstructured Data.

- Database: SQLite. One file, no server to run, and it loads straight into pandas for analysis. Move to Postgres only if concurrent writes become a problem; until then run a single uvicorn worker or enable WAL mode.
- Access layer: SQLAlchemy 2.0, with Alembic for migrations.
- Store headers (and any other unstructured data later) in a JSON column. That covers most of what a NoSQL store would give us, without running a second database.

### Frontend

Let's keep it minimal for the initial tests. We can start with a static page, then we run tests on it, see what we can find with the experiment. Then we could add more components, and details to the website and test again... repeat the process.

- Serve the static site from FastAPI (`StaticFiles`), not a separate web server, so requests for the favicon, CSS and fonts reach the request log.
- The static page must reference real CSS, a favicon and a web font. "Did the client fetch browser assets?" is one of the classifier's signals, and it only works if there are assets to fetch.
- Record the site version (git commit or a version tag) on every session. Each iteration changes what clients see, so data from different versions must be separable; otherwise a site change can look like a change in agent behaviour.

## Classifer Stack

For now we can use a python classifier using typical ML solutions. A nice learning experiment would be to build different levels of classifiers (KNN, Logistic Regression, RF, etc...)

- Libraries: scikit-learn and pandas.
- The ladder, simplest first:
  0. Majority-class baseline and a simple user-agent rule. If a one-line user-agent check already catches most agents, that is a finding worth reporting.
  1. KNN
  2. Logistic regression
  3. Random forest
  4. Gradient boosting
- Put KNN and logistic regression behind a `StandardScaler` in a scikit-learn `Pipeline`, since both are sensitive to feature scale. Random forest and gradient boosting don't need it.
- Score every rung with the same evaluation harness, including detection latency (how many requests before a session is flagged), so the comparison is fair.
