from sqlmodel import create_engine

# Connection string for PostgreSQL with pgvector
TAGGING_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/tag_embeddings"

# Create SQLAlchemy engine instance
TAGGING_DB_ENGINE = create_engine(TAGGING_DATABASE_URL)
