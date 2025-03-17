# OSM Tagger

As part of HOT's participation in @Tech To The Rescue, we are kickstarting a collaboration with our new tech partner [Fulton Ring](https://www.fultonring.com/) ! 🤝 
Together, we're diving into development of an AI-powered API for generating valid OSM tags from street-level imagery, which will be used by [ChatMap](https://chatmap.hotosm.org), a venture that promises to bring innovative solutions to the forefront of our mission.

## Setup & run

### Model

You'll need Ollama installed on your system:

https://ollama.com/

Then, depending on your hardware, select and download an Ollama model. 

Currently we support: `ollama/llava:34b` and `llama3.2-vision:11b`.

```sh
ollama pull ollama/llama3.2-vision:11b
```

Check `config/models.py`, you might need to enable the model there.

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


##  OSMTagger API

OSMTagger API should receive a request with an image URL, geo-location and category,  and return OSM valid tags. The category will help the API to decide a prompt and maybe other configurations.

Two models will be used, one focused on extracting text from an image and the other for generating OSM tags from the text. This will divide the problem in two and provide more flexibility for the final solution.




