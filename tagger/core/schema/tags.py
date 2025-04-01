from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from pgvector.sqlalchemy import Vector
from sqlmodel import SQLModel, Field
from geoalchemy2 import Geometry
import sqlalchemy as sa


class TagEmbedding(SQLModel, table=True):
    __tablename__ = "tag_embeddings"

    id: Optional[int] = Field(
        primary_key=True,
    )
    category: str = Field(index=True)
    image_url: str = Field(unique=True)
    attribution: Optional[str] = Field(default=None)
    image_embeddings: Sequence[float] = Field(sa_type=Vector(768))
    insert_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(datetime.UTC)
    )
    coordinates: Any = Field(sa_column=sa.Column(Geometry("POINT")))
    tags: Dict[str, str] = Field(sa_type=sa.JSON)


image_embeddings_index = sa.Index(
    "tag_embeddings_hnsw_cosine_similarity_idx",
    TagEmbedding.image_embeddings,
    postgresql_using="hnsw",
    postgresql_with={"m": 16, "ef_construction": 64},
    postgresql_ops={"image_embeddings": "vector_cosine_ops"},
)

location_index = sa.Index(
    "idx_tag_embeddings_location",
    "latitude",
    "longitude",
    postgresql_using="gist",
    postgresql_ops={"latitude": "point_ops", "longitude": "point_ops"},
)
