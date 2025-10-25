
import asyncio
import json
from sqlalchemy import create_engine, Column, String, DateTime, JSON, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get settings from config
try:
    from config import settings
except ImportError:
    logger.error("Could not import settings. Make sure your config.py and .env file are set up correctly.")
    exit(1)

# Import anomaly detection services
try:
    from services.anomaly_detection import AnomalyDetectionService
except ImportError:
    logger.error("Could not import AnomalyDetectionService. Ensure it exists and is accessible.")
    exit(1)

# SQLAlchemy setup
DATABASE_URL = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}/{settings.POSTGRES_DB}"
Base = declarative_base()

class Anomaly(Base):
    __tablename__ = 'anomalies'
    id = Column(String, primary_key=True)
    type = Column(String, nullable=False)
    location = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    description = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    recommended_actions = Column(JSON, nullable=True)
    entity_id = Column(String, nullable=True)

async def cache_anomalies():
    """
    Main function to fetch all historical anomalies and cache them in PostgreSQL.
    """
    logger.info("Starting anomaly caching process...")

    # Initialize database connection
    try:
        engine = create_engine(DATABASE_URL)
        # Drop and recreate the table to ensure schema is up to date
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        logger.info("Database connection successful and table created/verified.")
    except Exception as e:
        logger.error(f"Error connecting to the database: {e}")
        return

    # Initialize anomaly detection service
    try:
        anomaly_service = AnomalyDetectionService(
            neo4j_uri=settings.NEO4J_URI,
            neo4j_user=settings.NEO4J_USER,
            neo4j_password=settings.NEO4J_PASSWORD
        )
        logger.info("AnomalyDetectionService initialized.")
    except Exception as e:
        logger.error(f"Error initializing AnomalyDetectionService: {e}")
        db.close()
        return

    try:
        # 1. Fetch all historical anomalies (including entity-specific ones)
        logger.info("Fetching all historical anomalies...")
        all_anomalies = anomaly_service.get_all_historical_anomalies()
        logger.info(f"Fetched {len(all_anomalies)} anomalies in total.")

        if not all_anomalies:
            logger.info("No anomalies to cache.")
            return

        # 2. Add new anomalies to the database
        logger.info("Caching new anomalies...")
        cached_count = 0
        unique_ids = set()
        for anomaly_data in all_anomalies:
            anomaly_id = str(anomaly_data.get('id'))
            if anomaly_id in unique_ids:
                logger.warning(f"Duplicate anomaly ID found: {anomaly_id}. Skipping.")
                continue
            unique_ids.add(anomaly_id)

            # Ensure timestamp is a datetime object
            timestamp = anomaly_data.get('timestamp')
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except ValueError:
                    logger.warning(f"Could not parse timestamp string: {timestamp}. Skipping anomaly.")
                    continue
            
            if not isinstance(timestamp, datetime):
                 timestamp = datetime.now()

            # Create Anomaly object
            anomaly = Anomaly(
                id=anomaly_id,
                type=anomaly_data.get('type'),
                location=anomaly_data.get('location'),
                severity=anomaly_data.get('severity'),
                timestamp=timestamp,
                description=anomaly_data.get('description'),
                details=anomaly_data.get('details'),
                recommended_actions=anomaly_data.get('recommended_actions'),
                entity_id=anomaly_data.get('entity_id')
            )
            db.add(anomaly)
            cached_count += 1

        db.commit()
        logger.info(f"Successfully cached {cached_count} anomalies.")

    except Exception as e:
        logger.error(f"An error occurred during the caching process: {e}")
        db.rollback()
    finally:
        db.close()
        logger.info("Database connection closed.")

if __name__ == "__main__":
    asyncio.run(cache_anomalies())
