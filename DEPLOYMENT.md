# 🚀 Deployment Guide

This guide covers deploying the Voice Agent application to production.

## Frontend Deployment (Vercel)

### Step 1: Prepare Repository

1. Ensure all code is committed:
   ```bash
   git add .
   git commit -m "Ready for deployment"
   git push origin main
   ```

2. Verify `frontend/.env.local` is in `.gitignore` (it should be)

### Step 2: Deploy to Vercel

1. **Go to [vercel.com](https://vercel.com)** and sign in
2. Click **"New Project"**
3. Import your GitHub repository
4. Configure the project:
   - **Framework Preset**: Next.js (auto-detected)
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `.next` (default)
   - **Install Command**: `npm install` (default)

5. **Add Environment Variables**:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend-api.com
   NEXT_PUBLIC_LIVEKIT_URL=wss://your-project.livekit.cloud
   ```

6. Click **"Deploy"**

7. Your app will be live at `https://your-project.vercel.app`

### Step 3: Configure Custom Domain (Optional)

1. Go to Project Settings → Domains
2. Add your custom domain
3. Follow DNS configuration instructions

## Backend Deployment

The backend consists of two services:
1. **FastAPI Server** (`api.py`) - REST API
2. **LiveKit Agent** (`main.py`) - Voice agent worker

### Option 1: Railway (Recommended for Simplicity)

1. **Install Railway CLI**:
   ```bash
   npm i -g @railway/cli
   ```

2. **Login**:
   ```bash
   railway login
   ```

3. **Initialize Project**:
   ```bash
   railway init
   ```

4. **Add Environment Variables**:
   ```bash
   railway variables set LIVEKIT_URL=wss://your-project.livekit.cloud
   railway variables set LIVEKIT_API_KEY=your-key
   railway variables set LIVEKIT_API_SECRET=your-secret
   railway variables set DEEPGRAM_API_KEY=your-key
   railway variables set CARTESIA_API_KEY=your-key
   railway variables set OPENAI_API_KEY=your-key
   railway variables set BEY_API_KEY=your-key
   railway variables set BEY_AVATAR_ID=your-id
   railway variables set SUPABASE_URL=your-url
   railway variables set SUPABASE_KEY=your-key
   railway variables set SUPABASE_DB_PASSWORD=your-password
   railway variables set JWT_SECRET=your-secret
   ```

5. **Deploy API Server**:
   - Create a new service
   - Set start command: `cd backend && python api.py`
   - Railway will auto-detect Python

6. **Deploy LiveKit Agent**:
   - Create another service
   - Set start command: `cd backend && python main.py start`
   - This runs as a background worker

### Option 2: Render

1. **Create Web Service** (for API):
   - New → Web Service
   - Connect GitHub repo
   - Build: `pip install -r requirements.txt`
   - Start: `cd backend && python api.py`
   - Add all environment variables

2. **Create Background Worker** (for Agent):
   - New → Background Worker
   - Same repo
   - Start: `cd backend && python main.py start`
   - Add all environment variables

### Option 3: DigitalOcean App Platform

1. Create app from GitHub
2. Add Python service
3. Configure:
   - Build: `pip install -r requirements.txt`
   - Run: `cd backend && python api.py`
4. Add environment variables
5. Create second service for agent worker

### Option 4: AWS/GCP/Azure

**AWS (EC2 or ECS)**:
- Use EC2 instance or ECS container
- Install Python dependencies
- Run with systemd or ECS task

**GCP (Cloud Run or Compute Engine)**:
- Cloud Run for serverless
- Compute Engine for persistent

**Azure (App Service or Container Instances)**:
- App Service for managed
- Container Instances for containers

## Environment Variables Checklist

Ensure all these are set in your deployment platform:

### Required for Backend:
- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `DEEPGRAM_API_KEY`
- `CARTESIA_API_KEY`
- `CARTESIA_VOICE_ID`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `BEY_API_KEY`
- `BEY_AVATAR_ID`
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SUPABASE_DB_PASSWORD` (optional, for auto table creation)
- `JWT_SECRET`

### Required for Frontend:
- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_LIVEKIT_URL`

## Post-Deployment Checklist

- [ ] Frontend deployed and accessible
- [ ] Backend API responding to health checks
- [ ] LiveKit agent running and connected
- [ ] Database tables created (check Supabase)
- [ ] Environment variables set correctly
- [ ] CORS configured (if needed)
- [ ] Test user flow: book appointment
- [ ] Test mentor login and calendar
- [ ] Test admin dashboard
- [ ] Verify cost tracking is working
- [ ] Check logs for errors

## Monitoring

### Frontend (Vercel)
- Check Vercel dashboard for build logs
- Monitor function execution times
- Check error logs

### Backend
- Monitor API response times
- Check agent logs for connection issues
- Monitor database connection pool
- Track cost metrics in Supabase

## Troubleshooting Deployment

### Build Fails
- Check Node.js version (18+)
- Verify all dependencies in `package.json`
- Check build logs for specific errors

### API Not Responding
- Verify backend is running
- Check environment variables
- Verify CORS settings
- Check firewall/security groups

### Agent Not Connecting
- Verify LiveKit credentials
- Check agent logs
- Ensure agent process is running
- Verify network connectivity to LiveKit

### Database Errors
- Check Supabase connection
- Verify credentials
- Run `schema.sql` manually if needed
- Check RLS policies

## Scaling

### Frontend (Vercel)
- Automatically scales
- No configuration needed

### Backend API
- Use load balancer for multiple instances
- Configure auto-scaling based on CPU/memory
- Use connection pooling for database

### LiveKit Agent
- Run multiple agent instances
- LiveKit handles load balancing
- Each agent can handle multiple concurrent sessions

## Security Considerations

1. **Never commit `.env` files**
2. **Use strong JWT_SECRET** (random, 32+ characters)
3. **Enable HTTPS** (Vercel does this automatically)
4. **Set up CORS** properly
5. **Use environment-specific API keys**
6. **Enable Supabase RLS** policies
7. **Rotate API keys** regularly
8. **Monitor for suspicious activity**

## Cost Optimization

1. **Use appropriate OpenAI model** (gpt-4o-mini is cost-effective)
2. **Monitor usage** in admin dashboard
3. **Set up alerts** for high costs
4. **Use caching** where possible
5. **Optimize database queries**
6. **Use CDN** for static assets (Vercel does this)

---

**Need Help?** Check the main [README.md](./README.md) or open an issue.
