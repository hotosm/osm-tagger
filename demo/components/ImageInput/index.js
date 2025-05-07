
import styles from './styles.css?inline';
import '@shoelace-style/shoelace/dist/components/button/button.js';
import '@shoelace-style/shoelace/dist/components/input/input.js';

class ImageInput extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: 'open' });
      this.onAction = this.getAttribute('onAction');
      this.defaultValue = this.getAttribute('defaultValue');
      const styleSheet = new CSSStyleSheet();
      styleSheet.replaceSync(styles);
      this.shadowRoot.adoptedStyleSheets = [styleSheet];

      this.shadowRoot.innerHTML = `
        <div class="form">

          <sl-input
              placeholder="Image URL"
              id="input"
              class="input"
              value="${this.defaultValue}"
          ></sl-input>

          <sl-button
              variant="primary"
              id="button"
              onclick="${this.onAction}"
          >
            <sl-icon
              name="stars"
            >
            </sl-icon>
            Get tags
          </sl-button>

        </div>

      `;
      this.input = this.shadowRoot.getElementById('input');
      this.button = this.shadowRoot.getElementById('button');
    }

    get value() {
        return this.input.value;
    }
}

customElements.define('image-input', ImageInput);
