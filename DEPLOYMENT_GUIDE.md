# Deployment Guide: Go Live in 5 Minutes 🚀

Since I've already created the `Dockerfile` and optimized the backend to serve the frontend, you can deploy this entire application to a public URL using **Railway** with almost zero configuration.

## Step 1: Push to GitHub
If your project isn't on GitHub yet, you'll need to create a repository and push your code there.
1. Create a new repository on [GitHub](https://github.com/new).
2. Run these commands in your project folder:
   ```bash
   git init
   git add .
   git commit -m "Public Release Version"
   git branch -M main
   git remote add origin https://github.com/your-username/your-repo-name.git
   git push -u origin main
   ```

## Step 2: Connect to Railway
1. Go to [Railway.app](https://railway.app/) and sign in with GitHub.
2. Click **+ New Project** > **Deploy from GitHub repo**.
3. Select your `market-research` repository.

## Step 3: Add Your API Keys
Railway needs your API keys to run the agents.
1. Click on your project in the Railway dashboard.
2. Go to the **Variables** tab.
3. Add the following keys from your `.env` file:
   - `GEMINI_API_KEY`: (Your key)
   - `GEMINI_MODEL`: `gemini-2.5-flash`
   - `TAVILY_API_KEY`: (Your key)
   - `GROQ_API_KEY`: (Your key - optional)

## Step 4: Automatic Deployment
Railway will detect the `Dockerfile` I created and automatically start the build process. 
- It will build your React frontend.
- It will set up the Python backend.
- It will start the server on a dynamic port.

## Step 5: Get Your Public URL
1. Once the deploy is finished, go to the **Settings** tab of your project in Railway.
2. Click **Generate Domain**.
3. You now have a public URL (e.g., `market-research-production.up.railway.app`) that you can send to anyone!

---

### Why this works:
- **Unified Hosting**: The backend serves the frontend from the `/dist` folder, so you don't need two separate hosting fees.
- **Docker-Powered**: The `Dockerfile` ensures it works exactly like it did on your local machine.
- **Gemini 2.5 Flash**: The system is pre-configured for high-speed, advanced research.

> [!TIP]
> **Share it!** Once you have your URL, you can stick it in that LinkedIn post we wrote earlier! 🚀
