import os

from sqlmodel import create_engine

db_host = os.getenv("DB_HOST", "localhost")
db_port = os.getenv("DB_PORT", "5432")
db_name = os.getenv("DB_NAME", "tag_embeddings")
db_user = os.getenv("DB_USER", "postgres")
db_password = os.getenv("DB_PASSWORD", "postgres")

# Connection string for PostgreSQL with pgvector
TAGGING_DATABASE_URL = (
    f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
)

# Create SQLAlchemy engine instance
TAGGING_DB_ENGINE = create_engine(TAGGING_DATABASE_URL)
