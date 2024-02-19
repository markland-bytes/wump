import dotenv from 'dotenv';
import cors from 'cors';
import express, { Express } from 'express';
// import { getLogger } from './lib/logging/logger';


// Load environment variables from .env file
dotenv.config();


// const logger = getLogger();

const startApplication = async () => {
  const app: Express = express();
  const port = process.env.PORT || 3000;

  // await initializeDbConnection();

  // if (process.env.SEED_DB === 'true') {
  //   const includeDevData = process.env.SEED_DB_DEV === 'true';
  //   await seedDatabase(includeDevData);
  // }
  // setupMiddleware(app);
  // app.use('/', apiRouter);

  app.listen(port, () => {
    // logger.info(
    //   `⚡️[server]: Server is running at thkjhkjhe url: http://localhost:${port}`
    // );
  });
};

const setupMiddleware = (app: Express) => {
  app.use(express.json());

  const corsOrigins = process.env.CORS_ORIGINS?.split(',') || [];
  app.use(
    cors({
      origin: corsOrigins,
      allowedHeaders: ['Authorization', 'Content-Type'],
      credentials: true,
    })
  );
  //app.use(authenticateUser);
};

// Start the app
startApplication();
