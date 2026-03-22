// https://nuxt.com/docs/api/configuration/nuxt-config
import tailwindcss from '@tailwindcss/vite'

export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  ssr: false,
  devtools: {
    enabled: true,

    timeline: {
      enabled: true
    }
  },
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
    '/api/**': { proxy: { to: `${process.env.BACKEND_URL || 'http://localhost:8000'}/api/**` } }
  },
  runtimeConfig: {
    public: {
      backendUrl: process.env.BACKEND_URL || 'http://localhost:8000'
    }
  }
})