import Http from './http.js';
import CONFIG from './config.js';

/*
    OSM Tagger API
*/

const getTagsRequest = url => {
    return {
        "category": "roads",
        "image": {
            "url": `${url}`,
            "coordinates": {
                "lat": -31.039293,
                "lon": -64.312332
            }
        }
    }
}

class API {
  constructor() {
      this.http = new Http();
  }

  async fetchTags(req, options ) {
      try {
          const url = `${CONFIG.API_URL}tags/`;
          const result = await this.http.post(url, getTagsRequest(req));
          return result;
      } catch (error) {
            options.onError && options.onError(error);
          throw error;
      }
  }
}

export default API;

