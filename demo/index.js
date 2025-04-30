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
    const DEFAULT_IMG = "https://wiki.openstreetmap.org/w/images/1/10/Potholes_at_the_Level_Crossing%2C_Barrow_Haven_-_geograph.org.uk_-_1621073.jpg";
    this.imgInput.setAttribute("defaultValue", DEFAULT_IMG);
    this.imgPreview.setAttribute("style", "background-image: url('https://wiki.openstreetmap.org/w/images/1/10/Potholes_at_the_Level_Crossing%2C_Barrow_Haven_-_geograph.org.uk_-_1621073.jpg')");
  }

  // Get tags from API and dispay results
  handleGetTagsClick = async () => {
    const api = new API();

    this.imgPreview.style = "";
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
      this.imgPreview.style = `background-image: url("${this.imgInput.value}")`;
    }

  };
}

export default Index;