
class ImageInput extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: 'open' });
      this.shadowRoot.innerHTML = `
        <input
            placeholder="Image URL"
            id="input"
            type="text"
            value="https://umap.hotosm.org/media_file/00000030-PHOTO-2025-02-04-07-03-24.jpg"
        />
        <button
            onclick="${this.getAttribute('onClick')}"
        >Get tags</button>
      `;
      this.input = this.shadowRoot.getElementById('input');
    }

    get value() {
        return this.input.value;
    }
}

customElements.define('image-input', ImageInput);
