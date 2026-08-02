## How to run

1. Install [Docker](https://docs.docker.com/get-docker/).
2. Copy `env.example` to `.env` and generate values for `JWT_SECRET` and
   `API_KEYS_ENCRYPTION_KEY` using the command shown in that file.
3. Start the application and PostgreSQL:

   ```bash
   docker compose up --build
   ```

The database schema is installed automatically on the first start and data is
kept in the `postgres_data` Docker volume.

For development outside Docker, install `backend/requirements.txt` and
`backend/requirements-dev.txt`, install the frontend packages with `npm install`,
and set `DATABASE_URL` to your PostgreSQL instance.

## Maintenance

```bash
ruff format backend/
cd frontend && npm run format && npm run check
```
