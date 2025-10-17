import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './style.css'

// Views
import CaptureView from './views/CaptureView.vue'
import SearchView from './views/SearchView.vue'
import GraphView from './views/GraphView.vue'

// Router configuration
const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'capture',
      component: CaptureView,
    },
    {
      path: '/search',
      name: 'search',
      component: SearchView,
    },
    {
      path: '/graph',
      name: 'graph',
      component: GraphView,
    },
  ],
})

const app = createApp(App)
app.use(router)
app.mount('#app')
