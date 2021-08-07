import {
    createLocalVue,
    mount
} from '@vue/test-utils';

import Home from 'components/Home.vue';

import BootstrapVue from 'bootstrap-vue';
import ReactiveStorage from "vue-reactive-localstorage";

const localVue = createLocalVue();
localVue.use(BootstrapVue);
localVue.use(ReactiveStorage, {
    "token": "",
    "isAdmin": false,
    "otherUserPk": 0,
    "loggedInUser": {}
});

describe('Home component', () => {
    it("Shows Create Account button if not logged in", async () => {
        localVue.prototype.$isLoggedIn = () => false;

        let wrapper = mount(Home, { localVue });

        expect(wrapper.text()).toContain("Crear cuenta");
        expect(wrapper.text()).not.toContain("Mi cuenta");
    });

    it("Shows My Account button if logged in", async () => {
        localVue.prototype.$isLoggedIn = () => true;

        let wrapper = mount(Home, { localVue });

        expect(wrapper.text()).not.toContain("Crear cuenta");
        expect(wrapper.text()).toContain("Mi cuenta");
    });
});