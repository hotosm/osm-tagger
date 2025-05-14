import { defineConfig } from 'vite'
import Unocss from 'unocss/vite'

export default defineConfig({
  base: '/osm-tagger/',
  plugins: [
    Unocss({
      configFile: './uno.config.ts', // explicitly point to your config
    }),
  ],
})