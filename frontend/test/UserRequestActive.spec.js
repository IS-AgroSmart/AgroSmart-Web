import {
    createLocalVue,
    mount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import UserRequestActive from 'components/UserRequestActive.vue';

import {
    DropdownPlugin,
    CardPlugin,
    LayoutPlugin,
    AlertPlugin,
    FormInputPlugin,
    FormPlugin
} from 'bootstrap-vue';
import ReactiveStorage from "vue-reactive-localstorage";

const localVue = createLocalVue();
localVue.use(DropdownPlugin);
localVue.use(CardPlugin);
localVue.use(LayoutPlugin);
localVue.use(AlertPlugin);
localVue.use(FormInputPlugin);
localVue.use(FormPlugin);
localVue.prototype.$isLoggedIn = () => true;
localVue.use(ReactiveStorage, {
    "token": "",
    "isAdmin": false,
    "otherUserPk": 0,
    "loggedInUser": {}
});

import axios from 'axios'
import MockAdapter from 'axios-mock-adapter';

describe('Active Users component', () => {
    let wrapper, mock;

    function mountComponent() {
        wrapper = mount(UserRequestActive, {
            localVue,
            mocks: {
                $bvModal: {
                    msgBoxConfirm: jest.fn((title, config) => Promise.resolve(true))
                },
                $bvToast: {
                    toast: jest.fn(),
                },
                $router: {
                    push: jest.fn(),
                }
            },
        });
    }

    beforeEach(() => {
        mock = new MockAdapter(axios);
        mock.onGet("api/users").replyOnce(200, [{
                pk: 1,
                username: "myname",
                email: "myname@example.com",
                type: "ACTIVE"
            },
            {
                pk: 2,
                username: "foo",
                email: "foo@example.com",
                type: "DELETED"
            },
            {
                pk: 3,
                username: "bar",
                email: "bar@example.com",
                type: "ACTIVE"
            },
            {
                pk: 4,
                username: "admin",
                email: "admin@gmail.com",
                type: "ADMIN"
            },
            {
                pk: 5,
                username: "demo",
                email: "demo@gmail.com",
                type: "DEMO_USER"
            },
        ]);
    });

    afterEach(function () {
        mock.restore();
    });

    it("only shows active users", async () => {
        mountComponent();
        await flushPromises();

        expect(wrapper.findAll(".card")).toHaveLength(3);
        expect(wrapper.text().includes("myname@example.com")).toBe(true);
        expect(wrapper.text().includes("foo@example.com")).toBe(false);
        expect(wrapper.text().includes("admin@gmail.com")).toBe(true);
        expect(wrapper.text().includes("bar@example.com")).toBe(true);
        expect(mock.history.get).toHaveLength(1);
    });

    it("redirects to login if not logged in", async () => {
        localVue.prototype.$isLoggedIn = () => false;
        mountComponent();
        await flushPromises();

        expect(wrapper.vm.$router.push).toHaveBeenCalled();
    });

    it("can delete a user", async () => {
        mountComponent();
        mock.onPatch(/api\/users\/\d+\//).replyOnce(200, {});

        wrapper.vm.accionRequest({
            pk: 1,
            email: "foo@foo",
            username: "foo"
        }, "Eliminar");
        await flushPromises();
        expect(mock.history.patch).toHaveLength(1);
        expect(JSON.parse(mock.history.patch[0].data)).toHaveProperty("type", "DELETED");
    });

    it("filters users if a search string is set", async () => {
        mountComponent();
        await flushPromises();
        wrapper.vm.opcionFilter = "example";

        await wrapper.vm.$nextTick(); // Allow for recomputing 
        expect(wrapper.findAll(".card")).toHaveLength(2);
        expect(wrapper.text().includes("myname@example.com")).toBe(true);
        expect(wrapper.text().includes("bar@example.com")).toBe(true);
        expect(wrapper.text().includes("admin@gmail.com")).toBe(false);
    });

    it("shows an error message on connection error when deleting", async () => {
        mountComponent();
        mock.onPatch(/api\/users\/\d+\//).networkError();

        wrapper.vm.accionRequest({
            pk: 1,
            email: "foo@foo",
            username: "foo"
        }, "Eliminar");
        await flushPromises();
        expect(mock.history.patch).toHaveLength(1);
        expect(wrapper.vm.$bvToast.toast).toHaveBeenCalled();
    });

    it("asks for confirmation before acting", async () => {
        mountComponent();
        mock.onPatch(/api\/users\/\d+\//).reply(200, {});

        wrapper.vm.accionRequest({
            pk: 1,
            email: "foo@foo",
            username: "foo"
        }, "Eliminar");

        await flushPromises();
        expect(wrapper.vm.$bvModal.msgBoxConfirm).toHaveBeenCalled();
    });

    it("navigates to Deleted Users window", async () => {
        mountComponent();
        await flushPromises();

        await wrapper.find("button.dropdown-item").trigger("click");
        expect(wrapper.vm.$router.push).toHaveBeenCalled();
    });
})