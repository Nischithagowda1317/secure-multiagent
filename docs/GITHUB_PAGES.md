# Publish the dashboard on GitHub Pages

The included workflow publishes `frontend/dist`, the ready-to-run dashboard.
It uses relative asset URLs so it works under `/secure-multiagent/` and with a
custom domain. It does not install Python backend packages or npm dependencies.

GitHub Pages serves static files. Without a hosted backend, the published site
shows a service setup screen. Login, AI answers, uploads, and data views require
the separately hosted FastAPI application; Pages cannot run the Python backend.

## Publish now

1. Push these changes to the `main` branch of
   `Nischithagowda1317/secure-multiagent`.
2. In the repository, open **Settings > Pages** and select **GitHub Actions**
   under **Build and deployment > Source**.
3. Open **Actions > Deploy dashboard to GitHub Pages > Run workflow** and select
   `main`. Subsequent pushes to `main` deploy automatically.
4. After the deployment succeeds, open
   https://nischithagowda1317.github.io/secure-multiagent/.

## Connect the backend later

1. Host the FastAPI application on an HTTPS server with persistent storage for
   its runtime data. Configure its models, datasets and backend `OPENAI_API_KEY`.
2. Set this environment variable on the **backend host**, then restart it:

   ```dotenv
   CORS_ORIGINS=https://nischithagowda1317.github.io
   ```

   Use only the origin, without `/secure-multiagent/` or a trailing slash.
   If you also need local development, append the localhost origins separated
   by commas. A custom Pages domain needs its own origin in this setting.
3. In GitHub, open **Settings > Secrets and variables > Actions > Variables**.
   Add a repository variable named `BACKEND_API_URL`, for example:

   ```text
   https://your-backend.example.com/api
   ```

   Replace the example with the actual reachable backend URL, including `/api`.
   This URL is public browser configuration; do not put passwords or API keys
   in it. The build rejects HTTP URLs and URLs containing credentials.
4. Run the Pages workflow again. Changing a repository variable alone does not
   trigger a deployment. The dashboard now displays its sign-in screen and
   sends requests to the configured backend.
5. Verify `/api/health` on the backend, then sign in and submit an assistant
   request on the Pages site. Connection failures usually mean the backend is
   unavailable, the API URL is incorrect, or its CORS origin is missing.

## Local behavior and builds

- Local FastAPI and React development continue to use `/api` through the default
  `config.js`. The Pages build writes a separate config in `pages-site`.
- The Pages artifact contains only HTML, CSS, JavaScript, and `.nojekyll`.
  Backend `.env`, datasets, models, uploads, and runtime databases are not copied.
- The workflow publishes the included plain JavaScript dashboard in
  `frontend/dist`; changes to React source alone must also be reflected there.
  This packaging script expects that supplied dashboard layout, not Vite's
  generated `assets` layout.
- To inspect an artifact locally, run
  `python scripts/build_github_pages.py --output pages-site` and
  `python -m http.server 8080 --directory pages-site`.
  The output directory must be new for each build.

Reference: [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
