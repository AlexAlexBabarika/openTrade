# Start and stop OpenTrade

OpenTrade runs on your computer through Docker. Your accounts, settings, saved
provider keys, and database remain on your computer when you stop the app.

## Before you start

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) on
   macOS or Windows. On Linux, install Docker Engine with Docker Compose v2.
2. Start Docker Desktop and wait until it says Docker is running.
3. Download and fully extract the OpenTrade folder. Do not run the launcher from
   inside a ZIP file.

You do not need to create an `.env` file, configure PostgreSQL, or obtain an API
key for the default experience.

## macOS

### Start

Double-click **`Start OpenTrade.command`** in the OpenTrade folder.

The launcher starts Docker Desktop if necessary, waits for OpenTrade to become
healthy, and opens the application in your default browser.

If macOS reports that the launcher cannot be opened, right-click it, choose
**Open**, and confirm. If it reports “permission denied,” open Terminal in the
OpenTrade folder and run this once:

```bash
chmod +x "Start OpenTrade.command" "Stop OpenTrade.command" scripts/*.sh
```

### Stop

Double-click **`Stop OpenTrade.command`**.

## Windows

### Start

Double-click **`Start OpenTrade.bat`** in the OpenTrade folder.

If Windows shows a security prompt, inspect the publisher/path, then choose the
option to run the file only if it is the launcher from the official OpenTrade
download.

### Stop

Double-click **`Stop OpenTrade.bat`**.

## Linux

Open a terminal in the OpenTrade folder and run:

```bash
./scripts/start-opentrade.sh
```

To stop OpenTrade:

```bash
./scripts/stop-opentrade.sh
```

If the scripts are not executable, run `chmod +x scripts/*.sh` once.

## Terminal alternative

The launchers run the equivalent of these commands:

```bash
docker compose up -d --wait
docker compose stop
```

After starting manually, open [http://localhost:8000](http://localhost:8000).
If `OPENTRADE_PORT` is set in `.env`, use that port instead.

## Does stopping delete anything?

No. The stop launchers and `docker compose stop` preserve all OpenTrade data.
You can start the application again later and continue where you left off.

> [!CAUTION]
> Do not run `docker compose down --volumes` unless you intentionally want to
> permanently delete every OpenTrade account, setting, saved key, and database
> record.

## If OpenTrade does not start

1. Confirm Docker Desktop is running.
2. Make sure another application is not using port `8000`.
3. Open a terminal in the OpenTrade folder and run:

   ```bash
   docker compose ps
   docker compose logs --tail=100 opentrade postgres
   ```

4. If port `8000` is occupied, create a file named `.env` in the OpenTrade
   folder containing, for example:

   ```dotenv
   OPENTRADE_PORT=8001
   ```

   Run the start launcher again; it will open the configured address.

For unresolved problems, use the
[OpenTrade issue tracker](https://github.com/AlexAlexBabarika/openTrade/issues/new/choose).
