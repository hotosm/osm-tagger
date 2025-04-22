FROM postgres:16

# Install necessary packages for PostGIS and pgvector
RUN apt-get update \
  && apt-get install -y \
  postgresql-16-postgis-3 \
  postgresql-16-postgis-3-scripts \
  build-essential \
  git \
  postgresql-server-dev-16

# Build and install pgvector
RUN git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git \
  && cd pgvector \
  && make \
  && make install

# Add initialization scripts
RUN echo 'CREATE EXTENSION IF NOT EXISTS postgis;' > /docker-entrypoint-initdb.d/10-postgis.sql \
  && echo 'CREATE EXTENSION IF NOT EXISTS vector;' > /docker-entrypoint-initdb.d/20-vector.sql

# Set environment variables
ENV POSTGRES_DB=tag_embeddings
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=postgres

EXPOSE 5432
