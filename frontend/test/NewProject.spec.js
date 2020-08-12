import {
    createLocalVue,
    mount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import NewProject from 'components/NewProject.vue';

import BootstrapVue from 'bootstrap-vue';
import ReactiveStorage from "vue-reactive-localstorage";
import VueRouter from 'vue-router';
import Multiselect from 'vue-multiselect';

const localVue = createLocalVue();
localVue.prototype.$isLoggedIn = () => true;
localVue.use(BootstrapVue);
localVue.component('multiselect', Multiselect);
localVue.use(ReactiveStorage, {
    "token": "",
    "isAdmin": false,
    "otherUserPk": 0,
    "loggedInUser": {}
});
localVue.use(VueRouter);
const router = new VueRouter({});

import axios from 'axios'
import MockAdapter from 'axios-mock-adapter';

describe('New Project component', () => {
    let wrapper, mock;

    beforeEach(() => {
        wrapper = mount(NewProject, {
            localVue, router
        });
        mock = new MockAdapter(axios);
    });

    afterEach(function () {
        mock.restore();
    });

    /*it("calls the /api/flights endpoint when created", async () => {
        mock.onGet("api/flights/").reply(200);
        await flushPromises();
        expect(mock.history.get).toHaveLength(1);
    });*/

    it("posts correctly if all successful", async () => {
        mock.onPost("api/projects/").reply(200, {});

        wrapper.find('form').trigger('submit');
        await flushPromises();

        expect(mock.history.post).toHaveLength(1);

        expect(wrapper.find('.alert-danger').exists()).toBeFalsy();
    });
});