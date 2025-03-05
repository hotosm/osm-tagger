
As part of HOT's participation in @Tech To The Rescue, we are kickstarting a collaboration with our new tech partner [Fulton Ring](https://www.fultonring.com/) ! 🤝 
Together, we're diving into development of an AI-powered API for generating valid OSM tags from street-level imagery, which will be used by [ChatMap](https://chatmap.hotosm.org), a venture that promises to bring innovative solutions to the forefront of our mission.

ChatMap

ChatMap (chatmap.hotosm.org) is a simple but powerful app that enables mapping using common instant messaging apps like WhatsApp, Signal or Telegram.

This is how it works:

Someone creates a chat group
People post locations and messages
The chat is exported from the instant messaging app and loaded into ChatMap for creating a map

Messages can include text, image or video.

For persisting the data, media can be uploaded to a S3 bucket and the map’s GeoJSON to uMap (umap.hotosm.org)


OSMTagger API

OSMTagger API should receive a request with an image URL, geo-location and category,  and return OSM valid tags. The category will help the API to decide a prompt and maybe other configurations.

Two models will be used, one focused on extracting text from an image and the other for generating OSM tags from the text. This will divide the problem in two and provide more flexibility for the final solution.




