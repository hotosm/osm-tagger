import API from './services/API.js';

/* 
   Index page
*/

class Index {

  constructor() {
    this.imgInput = document.querySelector("#imageInput");
    this.tagList = document.querySelector("#tagList");
    this.loading = document.querySelector("#loadingMsg");
  }

  // Get tags from API and dispay results
  handleGetTagsClick = async () => {
    const api = new API();

    // Show loading message
    this.loading.classList.add("show");

    // // Fetch tags from API
    const result = await api.fetchTags(
        this.imgInput.value, 
        { onError: (error) => { console.log(error) } }
    );

    // Hide loading message
    this.loading.classList.remove("show");

    // Update page
    if (result && result.tags) {
      this.tagList.data = result.tags;
    }

  };
}

export default Index;