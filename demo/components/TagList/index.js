
class TagList extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.shadowRoot.innerHTML = `
        <ul id="tagList">
          <template id="tagTemplate">
            <li class="tag">
              <span class="key"></span> = <span class="value"></span>
              (<span class="confidence"></span>)
            </li>
          </template>
      </ul>
    `
    this.tagList = this.shadowRoot.getElementById('tagList');
    this.tagTemplate = this.shadowRoot.getElementById('tagTemplate');
  }

   /**
   * Add a tag element
   * @param {string} tag - Tag string
   */
  addTag(tag) {
    const instance = this.tagTemplate.content.cloneNode(true);
    const key = instance.querySelector('.key');
    const value = instance.querySelector('.value');
    const confidence = instance.querySelector('.confidence');
    
    key.textContent = tag.key;
    value.textContent = tag.value;
    confidence.textContent = tag.confidence;

    this.tagList.appendChild(instance);
  }

  /**
   * Sets the tags to display
   * @param {string[]} tags - Array of tag strings
   */
  set data(tags) {

    // Clear existing tags
    this.tagList.innerHTML = '';
    
    // Add new tags
    tags.forEach(tag => {
      this.addTag(tag);
    });
  }

}

customElements.define('tag-list', TagList);

