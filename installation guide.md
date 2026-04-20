## How to Run

1. **Install Supabase CLI**
   [Install guide](https://supabase.com/docs/guides/cli)

2. **Install Requiered packages**
    ```bash
    pip install -r backend/requirements.txt
    pip install -r backend/requirements-dev.txt
    cd frontend && npm install
    ```

2. **Start Supabase**
   ```bash
   supabase start
   ```

3. **Configure Environment Variables**
   - Copy `.env.example` to `.env`
   - Fill in any required values in `.env`

4. **Install Docker**
   [Get Docker](https://docs.docker.com/get-docker/)

5. **Build and Start Services with Docker Compose**
   ```bash
   docker compose up --build
   ```

## To maintain
1. **Format python code**
    ```bash
    ruff format backend/
    ```
2. **Format ts code**
    ```bash
    npm run format
    ```
3. **Check ts code for errors**
    ```bash
    npm run check
    ```
