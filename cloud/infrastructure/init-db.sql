-- ApexAurum Cloud - Database Initialization
-- This runs automatically when PostgreSQL container starts

-- Enable pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create initial schema (Alembic will manage migrations after this)
-- This is just for quick dev setup

-- Note: Full schema is managed by Alembic migrations
-- This file just ensures extensions are enabled
