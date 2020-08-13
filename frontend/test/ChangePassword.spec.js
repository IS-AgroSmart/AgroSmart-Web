import {
    createLocalVue,
    mount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import ChangePassword from 'components/ChangePassword.vue';

import BootstrapVue from 'bootstrap-vue';
import ReactiveStorage from "vue-reactive-localstorage";
import VueRouter from 'vue-router';

const localVue = createLocalVue();
localVue.use(BootstrapVue);
localVue.use(ReactiveStorage, {
    "token": "newtoken",
    "isAdmin": false,
    "otherUserPk": 0,
    "loggedInUser": {
        pk: 246
    }
});
localVue.use(VueRouter);
const router = new VueRouter({});

import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';

describe('Change password component', () => {
    let wrapper, mock;

    beforeEach(() => {
        wrapper = mount(ChangePassword, {
            localVue,
            router
        });
        mock = new MockAdapter(axios);
    });

    afterEach(function () {
        mock.restore();
    });

    it("sends API request", async () => {
        mock.onPost(/api\/users\/\d+\/set_password/).reply(200);

        wrapper.vm.form.password = "mynewpassword";
        wrapper.vm.form.repeatedPassword = "mynewpassword";
        wrapper.find('form').trigger('submit');
        await flushPromises();
        expect(wrapper.find('.alert-danger').exists()).toBeFalsy();
        expect(mock.history.post).toHaveLength(1);
        expect(JSON.parse(mock.history.post[0].data)).toHaveProperty("password", "mynewpassword");
        expect(mock.history.post[0].headers).toHaveProperty("Authorization", "Token newtoken");
    });

    it("doesn't send request when password is too short", async () => {
        mock.onPost(/api\/users\/\d+\/set_password/).reply(200);

        wrapper.vm.form.password = "new";
        wrapper.vm.form.repeatedPassword = "new";
        wrapper.find('form').trigger('submit');
        await flushPromises();

        expect(wrapper.find('.alert-danger').exists()).toBe(true);
        expect(mock.history.post).toHaveLength(0);
    });

    it("doesn't send request when passwords are different", async () => {
        mock.onPost(/api\/users\/\d+\/set_password/).reply(200);

        wrapper.vm.form.password = "new";
        wrapper.vm.form.repeatedPassword = "newpass";
        wrapper.find('form').trigger('submit');
        await flushPromises();

        expect(wrapper.find('.alert-danger').exists()).toBe(true);
        expect(mock.history.post).toHaveLength(0);
    });

    it("shows feedback when API returns errors", async () => {
        mock.onPost(/api\/users\/\d+\/set_password/).reply(400, {
            password: ["too short!", "not funny enough!"]
        });

        wrapper.vm.form.password = "newpassword";
        wrapper.vm.form.repeatedPassword = "newpassword";
        wrapper.find('form').trigger('submit');
        await flushPromises();

        expect(wrapper.find('.alert-danger').exists()).toBe(true);
        expect(mock.history.post).toHaveLength(1);
        expect(wrapper.text()).toContain("Error al cambiar contraseña");
    });

    it("shows feedback when network error", async () => {
        mock.onPost(/api\/users\/\d+\/set_password/).networkError();

        wrapper.vm.form.password = "newpassword";
        wrapper.vm.form.repeatedPassword = "newpassword";
        wrapper.find('form').trigger('submit');
        await flushPromises();

        expect(wrapper.find('.alert-danger').exists()).toBe(true);
        expect(mock.history.post).toHaveLength(1);
    });
});