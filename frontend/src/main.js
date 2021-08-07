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
import ProjectMap from './components/ProjectMap'
import UploadShapefile from './components/UploadShapefile'
import UploadGeotiff from './components/UploadGeotiff'
import CreateIndex from './components/CreateIndex'
import NewFlight from './components/NewFlight'
import Project from './components/Project'
import NewProject from './components/NewProject'
import Login from './components/Login'
import Logout from './components/Logout'
import SignUp from './components/SignUp'
import AdminHomepage from './components/AdminHomepage'
import RestorePassword from './components/RestorePassword'
import NewPassword from './components/NewPassword'
import UserRequests from "./components/UserRequests";
import Profile from './components/Profile'
import ChangePassword from './components/ChangePassword'
import userRequestDeleted from './components/UserRequestDeleted'
import userRequestActive from './components/UserRequestActive'
import userDeleted from "./components/UserDeleted"
import blockCriteria from "./components/BlockCriteria"
import DeletedProjects from "./components/DeletedProjects"

Vue.use(VueRouter);
Vue.use(BootstrapVue);
Vue.use(ReactiveStorage, {
  "token": "",
  "isAdmin": false, 
  "otherUserPk": 0,
  "loggedInUser": {}
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
Vue.use(vueDebounce);

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
    { path: '/projects/deleted', component: DeletedProjects },
    { path: '/projects/:uuid', name: "projectMap", component: ProjectMap },
    { path: '/projects/:uuid/upload/shapefile', name: "uploadShapefile", component: UploadShapefile },
    { path: '/projects/:uuid/upload/geotiff', name: "uploadGeotiff", component: UploadGeotiff },
    { path: '/projects/:uuid/upload/index', name: "createIndex", component: CreateIndex },
    { path: '/projects/new', name: 'newProject', component: NewProject },
    { path: '/login', component: Login },
    { path: '/logout', component: Logout },
    { path: '/signup', name: 'signUp', component: SignUp },
    { path: '/restorePassword', name: 'restorePassword', component: RestorePassword},
    { path: '/restorePassword/reset', name: 'newPassword', component: NewPassword},
    { path: '/admin', name: 'adminHome', component: AdminHomepage },
    { path: '/profile', name: 'profile',component: Profile },
    { path: '/changePassword', name: 'changePassword', component:ChangePassword},
    { path: '/admin/accountRequest', name:"userRequests", component:UserRequests},
    { path: '/admin/accountRequestActive', name:"userRequestActive", component:userRequestActive},
    { path: '/admin/accountRequestDeleted', name:"userRequestDeleted",component:userRequestDeleted},
    { path: '/admin/userDeleted', name:"userDeleted",component:userDeleted},
    { path: '/admin/blockCriteria', name:"blockCriteria",component:blockCriteria},
  ]
});

Vue.config.productionTip = false;
Vue.config.devtools = true;

Vue.prototype.$isLoggedIn = function() {
  return this.storage.token != undefined && this.storage.token != "";
}
Vue.prototype.$isAdmin = function() {
  return this.storage.isAdmin != undefined && this.storage.isAdmin;
}
Vue.prototype.$isMasquerading = function() {
  if(this.storage.otherUserPk != undefined && this.storage.otherUserPk != "") return this.storage.otherUserPk;
  else return null;
}
Vue.prototype.$effectiveUser = function() {
  if(!this.$isLoggedIn()) return null;
  // Try to use masqueraded user, if null then revert to logged in
  return this.$isMasquerading() ?? this.storage.loggedInUser; 
}
Vue.prototype.$cameras = [
  { text: 'Micasense Rededge', value: "REDEDGE" },
  { text: 'RGB', value: "RGB" }
];
Vue.prototype.$processingStepsODM = {
  10: "En cola",
  20: "Procesando",
  30: "Fallido",
  40: "Terminado",
  50: "Cancelado"
}
Vue.prototype.$processingStepsDjango = {
  "WAITING": "En cola",
  "PROCESSING": "Procesando",
  "ERROR": "Fallido",
  "COMPLETE": "Terminado",
  "CANCELED": "Cancelado"
}

new Vue({
  router,
  render: h => h(App)
}).$mount('#app')
