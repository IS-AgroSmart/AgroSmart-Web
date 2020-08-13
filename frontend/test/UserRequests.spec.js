import {
    createLocalVue,
    mount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import UserRequests from 'components/UserRequests.vue';

import {
    DropdownPlugin,
    CardPlugin,
    LayoutPlugin,
    AlertPlugin,
    FormInputPlugin,
    FormPlugin
} from 'bootstrap-vue';
import ReactiveStorage from "vue-reactive-localstorage";

import VueRouter from 'vue-router';

const localVue = createLocalVue();
localVue.use(DropdownPlugin);
localVue.use(CardPlugin);
localVue.use(LayoutPlugin);
localVue.use(AlertPlugin);
localVue.use(FormInputPlugin);
localVue.use(FormPlugin);
localVue.use(VueRouter);
const router = new VueRouter({});
localVue.prototype.$isLoggedIn = () => true;
localVue.use(ReactiveStorage, {
    "token": "",
    "isAdmin": false,
    "otherUserPk": 0,
    "loggedInUser": {}
});

import axios from 'axios'
import MockAdapter from 'axios-mock-adapter';

const createContainer = (tag = "div") => {
    const container = document.createElement(tag)
    document.body.appendChild(container)
    return container
};

describe('Pending requests component', () => {
    let wrapper, mock;

    beforeEach(() => {
        mock = new MockAdapter(axios);
        mock.onGet("api/users").replyOnce(200, [{
                pk: 1,
                username: "myname",
                email: "myname@example.com",
                type: "DEMO_USER"
            },
            {
                pk: 2,
                username: "foo",
                email: "foo@example.com",
                type: "ACTIVE"
            },
            {
                pk: 3,
                username: "bar",
                email: "bar@example.com",
                type: "DEMO_USER"
            },
            {
                pk: 4,
                username: "admin",
                email: "admin@gmail.com",
                type: "ADMIN"
            },
        ]);
        wrapper = mount(UserRequests, {
            localVue,
            router,
            mocks: {
                $bvModal: {
                    msgBoxConfirm: jest.fn((title, config) => Promise.resolve(true))
                },
                $bvToast: {
                    toast: jest.fn(),
                },
            },
        });
    });

    afterEach(function () {
        mock.restore();
    });

    it("only shows demo users", async () => {
        await flushPromises();

        expect(wrapper.findAll(".card").length).toBe(2);
        expect(wrapper.text().includes("myname@example.com")).toBeTruthy();
        expect(wrapper.text().includes("foo@example.com")).toBeFalsy();
        expect(wrapper.text().includes("admin@gmail.com")).toBeFalsy();
        expect(wrapper.text().includes("bar@example.com")).toBeTruthy();
        expect(mock.history.get.length).toBe(1);
    });

    it("can approve a user request", async () => {
        mock.onPatch(/api\/users\/\d+\//).replyOnce(200, {});

        wrapper.vm.accionRequest({
            pk: 1,
            email: "foo@foo",
            username: "foo"
        }, "Aceptar");
        await flushPromises();
        expect(JSON.parse(mock.history.patch[0].data).type).toBe("ACTIVE");
    });

    it("filters users if a search string is set", async () => {
        await flushPromises();
        wrapper.vm.opcionFilter = "myname";

        wrapper.vm.$nextTick(() => { // Allow for recomputing 
            expect(wrapper.findAll(".card").length).toBe(1);
            expect(wrapper.text().includes("myname@example.com")).toBeTruthy();
            expect(wrapper.text().includes("bar@example.com")).toBeFalsy();
        });
    })

    it("can reject a user request", async () => {
        mock.onPatch(/api\/users\/\d+\//).replyOnce(200, {});

        wrapper.vm.accionRequest({
            pk: 1,
            email: "foo@foo",
            username: "foo"
        }, "Rechazar");

        await flushPromises();
        expect(JSON.parse(mock.history.patch[0].data).type).toBe("DELETED");
    });

    it("shows an error message on connection error", async () => {
        mock.onPatch(/api\/users\/\d+\//).networkError();

        wrapper.vm.accionRequest({
            pk: 1,
            email: "foo@foo",
            username: "foo"
        }, "Aceptar");
        await flushPromises();
        expect(JSON.parse(mock.history.patch[0].data).type).toBe("ACTIVE");
        await wrapper.vm.$nextTick();
    });
})