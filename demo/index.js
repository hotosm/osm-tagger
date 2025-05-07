import API from './services/API.js';

/* 
   Index page
*/

class Index {

  constructor() {
    this.imgInput = document.querySelector("#imageInput");
    this.tagList = document.querySelector("#tagList");
    this.loading = document.querySelector("#loadingMsg");
    this.imgPreview = document.querySelector("#imgPreview");
    this.error = document.querySelector("#errorMsg");
    this.init();
  }

  init = () => {
    const DEFAULT_IMG = "https://umap.hotosm.org/media_file/00000030-PHOTO-2025-02-04-07-03-24.jpg";
    this.imgInput.setAttribute("defaultValue", DEFAULT_IMG);
    this.imgPreview.setAttribute("style", `background-image: url('${DEFAULT_IMG}')`);
  }

  // Get tags from API and dispay results
  handleGetTagsClick = async () => {
    const api = new API();

    this.imgPreview.setAttribute("style", `background-image: url('${this.imgInput.value}')`);
    this.tagList.data = [];

    // Show loading message
    this.loading.classList.add("show");
    // Hide any error message
    this.error.removeAttribute("open");
    // Disable input
    this.imgInput.setAttribute("disabled", "true");

    // // Fetch tags from API
    const result = await api.fetchTags(
        this.imgInput.value, { 
          onError: (error) => { 
            this.loading.classList.remove("show");
            this.error.setAttribute("open", "true");
            return false;
          } 
        }
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