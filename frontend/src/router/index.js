import { getToken } from '@/utils/auth'
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/home' },
    {
      path: '/',
      name: 'Layout',
      component: () => import('@/layouts/Layout.vue'),
      children: [
        { path: 'home', name: 'Home', component: () => import('@/views/Home.vue') },
        { path: 'seat', name: 'Seat', component: () => import('@/views/Seat.vue') },
        { path: 'books', name: 'Books', component: () => import('@/views/Books.vue') },
        { path: 'books/:id', name: 'BookDetail', component: () => import('@/views/BookDetail.vue') },
        { path: 'my', name: 'My', component: () => import('@/views/My.vue') },
        { path: 'admin/areas', name: 'AdminAreas', component: () => import('@/views/AdminAreas.vue') },
        { path: 'admin/seats', name: 'AdminSeats', component: () => import('@/views/AdminSeats.vue') },
        { path: 'admin/reservations', name: 'AdminReservations', component: () => import('@/views/AdminReservations.vue') },
        { path: 'admin/categories', name: 'AdminCategories', component: () => import('@/views/AdminCategories.vue') },
        { path: 'admin/books', name: 'AdminBooks', component: () => import('@/views/AdminBooks.vue') },
        { path: 'admin/borrows', name: 'AdminBorrows', component: () => import('@/views/AdminBorrows.vue') },
        { path: 'profile', name: 'Profile', component: () => import('@/views/Profile.vue') },
        { path: 'password', name: 'Password', component: () => import('@/views/Password.vue') },
        { path: 'user', name: 'User', component: () => import('@/views/User.vue') },
        {path: 'ai-chat',name: 'AIChat',component: () => import('@/views/AIChat.vue')}
      ]
    },
    { path: '/login', name: 'Login', component: () => import('@/views/Login.vue') },
    { path: '/register', name: 'Register', component: () => import('@/views/Register.vue') }
  ]
})

//路由守卫:验证token
router.beforeEach((to, from,) => {
  const token = getToken()
      if (to.path === '/login' || to.path === '/register') { 
        return true

      } else {
      return token ? true :'/login'
      } 
})
export default router
