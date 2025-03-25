from datetime import datetime
import json

from sqlalchemy import create_engine
from sqlmodel import Session
import pandas as pd

from tagger.core.schema.tags import TagEmbedding


def main():
    # Create database connection
    engine = create_engine(
        "postgresql://postgres:postgres@localhost:5432/tag_embeddings"
    )

    # Read the parquet file
    df = pd.read_parquet("./data/roads/road_image_embeddings.parquet")

    # Insert records in batches
    batch_size = 1000
    records_inserted = 0

    with Session(engine) as session:
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i : i + batch_size]

            embeddings = [
                TagEmbedding(
                    category=row["category"],
                    image_url=row["image_url"],
                    attribution=row["attribution"],
                    image_embeddings=row["image_embeddings"],
                    insert_timestamp=datetime.fromisoformat(row["insert_timestamp"]),
                    coordinates=f"POINT({row['latitude']} {row['longitude']})",
                    tags=json.loads(row["tags"]),
                )
                for _, row in batch.iterrows()
            ]

            session.bulk_save_objects(embeddings)
            session.commit()

            records_inserted += len(embeddings)
            print(f"Inserted {records_inserted} records")

    print(f"Successfully inserted {len(df)} records into the database")


if __name__ == "__main__":
    main()
