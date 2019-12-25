<template>
  <div id="app">
    <navbar></navbar>

    <div class="container pt-3">
      <router-view></router-view>
    </div>
  </div>
</template>

<script>
import Navbar from './components/Navbar'
export default {
  components: {
    Navbar
  }
}
</script>
