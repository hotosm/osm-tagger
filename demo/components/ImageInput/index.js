
import styles from './styles.css?inline';
import '@shoelace-style/shoelace/dist/components/button/button.js';
import '@shoelace-style/shoelace/dist/components/input/input.js';

class ImageInput extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: 'open' });
      this.onAction = this.getAttribute('onAction');
      const styleSheet = new CSSStyleSheet();
      styleSheet.replaceSync(styles);
      this.shadowRoot.adoptedStyleSheets = [styleSheet];

      this.shadowRoot.innerHTML = `
        <div class="form">

          <sl-input
              placeholder="Image URL"
              id="input"
              class="input"
              value="https://umap.hotosm.org/media_file/00000030-PHOTO-2025-02-04-07-03-24.jpg"
          ></sl-input>

          <sl-button
              variant="primary"
              onclick="${this.onAction}"
          >
            Get tags
          </sl-button>

        </div>

      `;
      this.input = this.shadowRoot.getElementById('input');
    }

    get value() {
        return this.input.value;
    }
}

customElements.define('image-input', ImageInput);
