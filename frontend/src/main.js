import Vue from 'vue'
import VueRouter from 'vue-router'
import BootstrapVue from 'bootstrap-vue'
import ReactiveStorage from "vue-reactive-localstorage";
import VueClipboard from 'vue-clipboard2';
import VueChatScroll from 'vue-chat-scroll';
import VueLayers from 'vuelayers'
import Multiselect from 'vue-multiselect'
import vueDebounce from 'vue-debounce'

import 'bootstrap/dist/css/bootstrap.css'
import 'bootstrap-vue/dist/bootstrap-vue.css'
import 'vuelayers/lib/style.css' // needs css-loader

import App from './App'
import Home from './components/Home'
import Flight from './components/Flight'
import DeletedFlights from './components/DeletedFlights'
import FlightDetails from './components/FlightDetails'
import FlightResults from './components/FlightResults'
import FlightReport from './components/FlightReport.vue'
import FlightOrthoPreview2 from './components/FlightOrthoPreview2'
import UploadImages from './components/UploadImages'
import UploadShapefile from './components/UploadShapefile'
import UploadGeotiff from './components/UploadGeotiff'
import CreateIndex from './components/CreateIndex'
import NewFlight from './components/NewFlight'
import Project from './components/Project'
import ProjectDetails from './components/ProjectDetails'
import NewProject from './components/NewProject'
import Login from './components/Login'
import Logout from './components/Logout'
import SignUp from './components/SignUp'
import RestorePassword from './components/RestorePassword'
import NewPassword from './components/NewPassword'

Vue.use(VueRouter);
Vue.use(BootstrapVue);
Vue.use(ReactiveStorage, {
  "token": "",
});
const moment = require('moment');
require('moment/locale/es');
Vue.use(require('vue-moment'), {
  moment
});
Vue.use(VueClipboard);
Vue.use(VueChatScroll);
Vue.use(VueLayers);
Vue.component('multiselect', Multiselect);
Vue.use(vueDebounce)

const router = new VueRouter({
  routes: [
    { path: '/', component: Home },
    { path: '/flights', component: Flight },
    { path: '/flights/deleted', component: DeletedFlights },
    { path: '/flights/:uuid', name: "flightDetails", component: FlightDetails },
    { path: '/flights/:uuid/upload', name: "uploadImages", component: UploadImages },
    { path: '/flights/:uuid/results', name: "flightResults", component: FlightResults },
    { path: '/flights/:uuid/report', name:"flightReport", component:FlightReport },
    { path: '/flights/:uuid/preview', name: "flightOrthoPreview", component: FlightOrthoPreview2 },
    { path: '/flights/new', name: "newFlight", component: NewFlight },
    { path: '/projects', name: "listProjects" ,component: Project },
    { path: '/projects/:uuid', name: "projectDetails", component: ProjectDetails },
    { path: '/projects/:uuid/upload/shapefile', name: "uploadShapefile", component: UploadShapefile },
    { path: '/projects/:uuid/upload/geotiff', name: "uploadGeotiff", component: UploadGeotiff },
    { path: '/projects/:uuid/upload/index', name: "createIndex", component: CreateIndex },
    { path: '/projects/new', name: 'newProject', component: NewProject },
    { path: '/login', component: Login },
    { path: '/logout', component: Logout },
    { path: '/signup', name: 'signUp', component: SignUp },
    { path: '/restorePassword', name: 'restorePassword', component: RestorePassword},
    { path: '/restorePassword/reset', name: 'newPassword', component: NewPassword},
  ]
})

Vue.config.productionTip = false;
Vue.config.devtools = true;

Vue.prototype.$isLoggedIn = function() {
  return this.storage.token != "";
}
Vue.prototype.$cameras = [
  { text: 'Micasense Rededge', value: "REDEDGE" },
  { text: 'RGB', value: "RGB" }
];
Vue.prototype.$processingSteps = {
  10: "En cola",
  20: "Procesando",
  30: "Fallido",
  40: "Terminado",
  50: "Cancelado"
}

new Vue({
  router,
  render: h => h(App)
}).$mount('#app')
