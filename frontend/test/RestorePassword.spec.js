import {
    createLocalVue,
    mount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import RestorePassword from 'components/RestorePassword.vue';

import BootstrapVue from 'bootstrap-vue';
import ReactiveStorage from "vue-reactive-localstorage";

const localVue = createLocalVue();
localVue.use(BootstrapVue);
localVue.prototype.$isLoggedIn = () => false;
localVue.use(ReactiveStorage, {
    "token": "",
    "isAdmin": false,
    "otherUserPk": 0,
    "loggedInUser": {}
});

import axios from 'axios'
import MockAdapter from 'axios-mock-adapter';

describe("Password reset component", () => {
    let wrapper, mock;

    const mountComponent = () => {
        wrapper = mount(RestorePassword, {
            localVue,
            stubs: ["router-link"],
            mocks: {
                $router: {
                    go: jest.fn(),
                }
            },
        });
    };

    beforeEach(() => {
        mock = new MockAdapter(axios);
    });

    afterEach(function () {
        mock.restore();
    });

    it("displays a single email input", async () => {
        mountComponent();
        await flushPromises();
        expect(wrapper.findAll("input")).toHaveLength(1);
        expect(wrapper.findAll("input[type=email]")).toHaveLength(1);
    });

    it("sends API request when Submit clicked", async () => {
        mock.onPost("api/password_reset/").reply(200, {});
        mountComponent();
        await flushPromises();
        await wrapper.find("input[type=email]").setValue("foo@example.com");
        await wrapper.vm.$nextTick();
        await wrapper.find("button[type=submit]").trigger("submit");
        await flushPromises();

        expect(mock.history.post).toHaveLength(1);
        expect(JSON.parse(mock.history.post[0].data)).toHaveProperty("email", "foo@example.com");

        expect(wrapper.vm.$router.go).toHaveBeenCalledWith(-1);
    });

    it("shows error message when API returns error", async () => {
        mock.onPost("api/password_reset/").reply(400, {email: ["not found"]});
        mountComponent();
        await flushPromises();
        await wrapper.find("input[type=email]").setValue("foo@example.com");
        await wrapper.vm.$nextTick();
        await wrapper.find("button[type=submit]").trigger("submit");
        await flushPromises();

        expect(wrapper.text()).toContain("Error! Verifique que el correo ingresado este vinculado con una cuenta de AgroSmart");
        expect(wrapper.vm.$router.go).not.toHaveBeenCalled();
    });

    it("shows error message when API returns network error", async () => {
        mock.onPost("api/password_reset/").networkError();
        mountComponent();
        await flushPromises();
        await wrapper.find("input[type=email]").setValue("foo@example.com");
        await wrapper.vm.$nextTick();
        await wrapper.find("button[type=submit]").trigger("submit");
        await flushPromises();

        expect(wrapper.text()).toContain("Error! Verifique que el correo ingresado este vinculado con una cuenta de AgroSmart");
        expect(wrapper.vm.$router.go).not.toHaveBeenCalled();
    });
})