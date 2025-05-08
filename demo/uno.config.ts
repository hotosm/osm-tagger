import { defineConfig, presetUno, transformerDirectives } from 'unocss'

export default defineConfig({
  presets: [
    presetUno(), // required for @apply directives
  ],
  transformers: [
    transformerDirectives(), // required for @apply
  ],
})