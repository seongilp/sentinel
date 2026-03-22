// https://nuxt.com/docs/api/configuration/nuxt-config
import tailwindcss from '@tailwindcss/vite'

export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  ssr: false,
  devtools: { enabled: true },
  css: ['~/assets/css/main.css'],
  components: {
    dirs: [
      { path: '~/components', ignore: ['**/ui/**'] }
    ]
  },
  vite: {
    plugins: [tailwindcss()]
  },
  routeRules: {
    '/api/**': { proxy: { to: 'http://localhost:8000/api/**' } }
  }
})
