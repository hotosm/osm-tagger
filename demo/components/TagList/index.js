import styles from './styles.css?inline';

class TagList extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    const styleSheet = new CSSStyleSheet();
    styleSheet.replaceSync(styles);
    this.shadowRoot.adoptedStyleSheets = [styleSheet];
    this.shadowRoot.innerHTML = `
      <table id="tagList" class="tagList">
        <template id="tagTemplate">
          <tr>
            <td class="key"></td>
            <td class="value"></td>
            <td class="confidence"></td>
          </tr>
        </template>
      </table>
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
    
    key.innerHTML = `<a \
      target="_blank" \
      href="https://wiki.openstreetmap.org/wiki/Key:${tag.key}">\
      ${tag.key}\
    </a>`;
    value.innerHTML = `<a \
      target="_blank" \
      href="https://wiki.openstreetmap.org/wiki/Tag:${tag.key}%3D${tag.value}">\
      ${tag.value}\
    </a>`;
    confidence.textContent = `${Math.round(tag.confidence * 100, 2)}%`;

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

