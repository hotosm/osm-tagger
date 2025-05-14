# OSM Tagger

As part of HOT's participation in @Tech To The Rescue, we are kickstarting a collaboration with our new tech partner [Fulton Ring](https://www.fultonring.com/) ! 🤝

Together, we're diving into development of an AI-powered API for generating valid OSM tags from street-level imagery, which will be used by [ChatMap](https://chatmap.hotosm.org), a venture that promises to bring innovative solutions to the forefront of our mission.

We kicked off the project in February/March 2025 and aim to have the work delivered by end of June 2025.

## Demo

Try it [here](https://hotosm.github.io/osm-tagger/)

## Setup & run

### Model (local)

For running OSM Tagger locally, you'll need [Ollama](https://ollama.com/) installed on your system.

Then, depending on your hardware, select and download an Ollama model.

Currently we support: `ollama/llava:34b` and `llama3.2-vision:11b`.

```sh
ollama pull ollama/llama3.2-vision:11b
```

And configure `config/models.py` accordingly.

_Note: you can also use Amazon Bedrock._

### Database & Storage

For local development and testing:

```sh
docker compose -f docker-compose.dev.yaml up -d
```

#### Database

Migrations and initial data for tagging roads:

```sh
poetry run alembic --name alembic revision --autogenerate
poetry run alembic --name alembic upgrade head
poetry run insert-image-embeddings
```

#### Storage

Go to the MinIO [admin](http://localhost:9001/browser) and setup a new bucket named `hotosm-osm-tagger`.

Then generate access keys and edit `config/models.py` un-commenting the lines for MinIO and adding the
credentials (`aws_access_key_id`, `aws_secret_access_key`).

You'll need to upload images to the Bucket, these are +9000 images of roads downloaded from Mapillary
that will help OSM Tagger to do the work and return a confidence value:

https://drive.google.com/file/d/1rNhUnXxmTjkCvbw6TuKc-0MgEIRsWxq4/view?usp=drive_link

Download the .zip file, un-compress it and upload the files to your bucket.

_Note: you can also use AWS S3_

### API

Install dependencies and run the API:

```sh
poetry install
uvicorn tagger.main:app --reload
```

Then, send a request with category and image (url and coordinates).

In this example we use "roads" and the image below:

<img src="https://umap.hotosm.org/media_file/00000030-PHOTO-2025-02-04-07-03-24.jpg" width="320" />

```
curl --request POST -H "Content-Type: application/json" \
  --url http://127.0.0.1:8000/api/v1/tags/ \
  --data '{
  "category": "roads",
  "image": {
    "url": "https://umap.hotosm.org/media_file/00000030-PHOTO-2025-02-04-07-03-24.jpg",
    "coordinates": {
      "lat": -31.039293,
      "lon": -64.312332
    }
  }
}'
```

You should receive a response with OSM tags:

```json
{
  "tags": [
    {
      "key": "smoothness",
      "value": "intermediate",
      "confidence": 0.6
    },
    {
      "key": "surface",
      "value": "unpaved",
      "confidence": 0.6
    }
  ]
}
```

## ChatMap

ChatMap (chatmap.hotosm.org) is a simple but powerful app that enables mapping using common instant messaging apps like WhatsApp, Signal or Telegram.

This is how it works:

Someone creates a chat group
People post locations and messages
The chat is exported from the instant messaging app and loaded into ChatMap for creating a map

Messages can include text, image or video.

For persisting the data, media can be uploaded to a S3 bucket and the map’s GeoJSON to uMap (umap.hotosm.org)

## OSMTagger API

OSMTagger API should receive a request with an image URL, geo-location and category, and return OSM valid tags. The category will help the API to decide a prompt and maybe other configurations.

Two models will be used, one focused on extracting text from an image and the other for generating OSM tags from the text. This will divide the problem in two and provide more flexibility for the final solution.
