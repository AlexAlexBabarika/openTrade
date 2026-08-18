# Start and stop OpenQuant

OpenQuant runs on your computer through Docker. Your accounts, settings, saved
provider keys, and database remain on your computer when you stop the app.

## Before you start

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) on
   macOS or Windows. On Linux, install Docker Engine with Docker Compose v2.
2. Start Docker Desktop and wait until it says Docker is running.
3. Download and fully extract the OpenQuant folder. Do not run the launcher from
   inside a ZIP file.

You do not need to create an `.env` file, configure PostgreSQL, or obtain an API
key for the default experience.

## macOS

### Start

Double-click **`Start OpenQuant.command`** in the OpenQuant folder.

The launcher starts Docker Desktop if necessary, waits for OpenQuant to become
healthy, and opens the application in your default browser.

If macOS reports that the launcher cannot be opened, right-click it, choose
**Open**, and confirm. If it reports “permission denied,” open Terminal in the
OpenQuant folder and run this once:

```bash
chmod +x "Start OpenQuant.command" "Stop OpenQuant.command" scripts/*.sh
```

### Stop

Double-click **`Stop OpenQuant.command`**.

## Windows

### Start

Double-click **`Start OpenQuant.bat`** in the OpenQuant folder.

If Windows shows a security prompt, inspect the publisher/path, then choose the
option to run the file only if it is the launcher from the official OpenQuant
download.

### Stop

Double-click **`Stop OpenQuant.bat`**.

## Linux

Open a terminal in the OpenQuant folder and run:

```bash
./scripts/start-openquant.sh
```

To stop OpenQuant:

```bash
./scripts/stop-openquant.sh
```

If the scripts are not executable, run `chmod +x scripts/*.sh` once.

## Terminal alternative

The launchers run the equivalent of these commands:

```bash
docker compose up -d --wait
docker compose stop
```

After starting manually, open [http://localhost:8000](http://localhost:8000).
If `OPENQUANT_PORT` is set in `.env`, use that port instead.

## Does stopping delete anything?

No. The stop launchers and `docker compose stop` preserve all OpenQuant data.
You can start the application again later and continue where you left off.

> [!CAUTION]
> Do not run `docker compose down --volumes` unless you intentionally want to
> permanently delete every OpenQuant account, setting, saved key, and database
> record.

## If OpenQuant does not start

1. Confirm Docker Desktop is running.
2. Make sure another application is not using port `8000`.
3. Open a terminal in the OpenQuant folder and run:

   ```bash
   docker compose ps
   docker compose logs --tail=100 openquant postgres
   ```

4. If port `8000` is occupied, create a file named `.env` in the OpenQuant
   folder containing, for example:

   ```dotenv
   OPENQUANT_PORT=8001
   ```

   Run the start launcher again; it will open the configured address.

For unresolved problems, use the
[OpenQuant issue tracker](https://github.com/AlexAlexBabarika/openQuant/issues/new/choose).
