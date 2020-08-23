import {
    createLocalVue,
    mount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import NewPassword from 'components/NewPassword.vue';

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
        wrapper = mount(NewPassword, {
            localVue,
            stubs: ["router-link"],
            mocks: {
                $route: {
                    query: {
                        token: "supersecrettoken"
                    }
                },
                $router: {
                    replace: jest.fn(),
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

    it("displays a single password input", async () => {
        mountComponent();
        await flushPromises();
        expect(wrapper.findAll("input[type=password]")).toHaveLength(1);
    });

    it("shows error message if less than 8 chars entered", async () => {
        mountComponent();
        await flushPromises();
        // neutral when box is empty
        expect(wrapper.find("input[type=password]").classes()).not.toContain("is-invalid");
        expect(wrapper.find("input[type=password]").classes()).not.toContain("is-valid");

        // invalid on short password
        await wrapper.find("input[type=password]").setValue("short");
        await wrapper.vm.$nextTick();
        expect(wrapper.find("input[type=password]").classes()).toContain("is-invalid");

        // valid on long password
        await wrapper.find("input[type=password]").setValue("longpassword");
        await wrapper.vm.$nextTick();
        expect(wrapper.find("input[type=password]").classes()).toContain("is-valid");
    });

    it("disables Submit button if short pass entered", async () => {
        mountComponent();
        await flushPromises();

        // disabled when box is empty or short password
        expect(wrapper.find("button[type=submit]").attributes()).toHaveProperty("disabled");
        await wrapper.find("input[type=password]").setValue("short");
        await wrapper.vm.$nextTick();
        expect(wrapper.find("button[type=submit]").attributes()).toHaveProperty("disabled");

        // enabled when long password
        await wrapper.find("input[type=password]").setValue("longpassword");
        await wrapper.vm.$nextTick();
        expect(wrapper.find("button[type=submit]").attributes()).not.toHaveProperty("disabled");
    });

    it("sends API request when Submit clicked", async () => {
        mock.onPost("api/password_reset/confirm/").reply(200, {});
        mountComponent();
        await flushPromises();
        await wrapper.find("input[type=password]").setValue("longpassword");
        await wrapper.vm.$nextTick();
        await wrapper.find("button[type=submit]").trigger("submit");
        await flushPromises();

        expect(mock.history.post).toHaveLength(1);
        expect(JSON.parse(mock.history.post[0].data)).toHaveProperty("token", "supersecrettoken");
        expect(JSON.parse(mock.history.post[0].data)).toHaveProperty("password", "longpassword");

        expect(wrapper.vm.$router.replace).toHaveBeenCalledWith({path: "/login"});
    });

    it("shows error message when API returns error", async () => {
        mock.onPost("api/password_reset/confirm/").reply(400, {password: ["too short"]});
        mountComponent();
        await flushPromises();
        await wrapper.find("input[type=password]").setValue("longpassword");
        await wrapper.vm.$nextTick();
        await wrapper.find("button[type=submit]").trigger("submit");
        await flushPromises();

        expect(wrapper.text()).toContain("password: too short");
        expect(wrapper.vm.$router.replace).not.toHaveBeenCalled();
    });

    it("shows error message when API returns network error", async () => {
        mock.onPost("api/password_reset/confirm/").networkError();
        mountComponent();
        await flushPromises();
        await wrapper.find("input[type=password]").setValue("longpassword");
        await wrapper.vm.$nextTick();
        await wrapper.find("button[type=submit]").trigger("submit");
        await flushPromises();

        expect(wrapper.text()).toContain("Network Error");
        expect(wrapper.vm.$router.replace).not.toHaveBeenCalled();
    });
})