import {
    createLocalVue,
    mount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import Flight from 'components/Flight.vue';

import BootstrapVue from 'bootstrap-vue';
import ReactiveStorage from "vue-reactive-localstorage";

const localVue = createLocalVue();
localVue.use(BootstrapVue);
localVue.prototype.$isLoggedIn = () => true;
localVue.use(ReactiveStorage, {
    "token": "",
    "isAdmin": false,
    "otherUserPk": 0,
    "loggedInUser": {
        type: "DEMO_USER",
        used_space: 50 * Math.pow(1024, 2),
        maximum_space: 120 * Math.pow(1024, 2)
    }
});


import axios from 'axios'
import MockAdapter from 'axios-mock-adapter';

jest.useFakeTimers();

describe("Flight list component", () => {
    let wrapper, mock;

    const mountComponent = () => {
        wrapper = mount(Flight, {
            localVue
        });
    };

    const mockApi = (url, responseData, valid = true) => {
        if (valid) mock.onGet(url).reply(200, responseData);
        else mock.onGet(url).networkError();
    };

    const mockFlights = (valid = true) => mockApi("api/flights", [{
        uuid: "uuid",
        camera: "RGB",
        processing_time: 6000,
        state: "PROCESSING",
        date: "2020-01-01",
        name: "Example flight",
        annotations: "Some example annotations",
        nodeodm_info: {
            progress: 40,
        },
        is_demo: false,
    }, {
        uuid: "uuid2",
        camera: "RGB",
        processing_time: 6000,
        state: "COMPLETE",
        date: "2020-01-01",
        name: "Completed flight",
        annotations: "More example annotations",
        nodeodm_info: {
            progress: 100,
        },
        is_demo: false,
    }, {
        uuid: "uuid3",
        camera: "RGB",
        processing_time: 6000,
        state: "COMPLETE",
        date: "2020-01-01",
        name: "Completed demo flight",
        annotations: "More example annotations",
        nodeodm_info: {
            progress: 100,
        },
        is_demo: true,
    }], valid);

    beforeEach(() => {
        mock = new MockAdapter(axios);
    });

    afterEach(function () {
        mock.restore();
        wrapper.vm.storage.otherUserPk = 0;
    });

    it("shows a list with flights", async () => {
        mockFlights();
        mountComponent();
        await flushPromises();

        expect(wrapper.text()).toContain("Example flight");
        expect(wrapper.text()).toContain("Some example annotations");
        expect(wrapper.text()).toContain("Completed demo flight");
        expect(wrapper.text()).toContain("Completed flight");

        // 1st is /api/users, 2nd is /api/flights/uuid
        expect(mock.history.get).toHaveLength(2);
    });

    it("correctly identifies demo flights", async () => {
        mockFlights();
        mountComponent();
        await flushPromises();

        expect(wrapper.text()).toContain("Completed demo flight (DEMO)");
        expect(wrapper.text()).not.toContain("Completed flight (DEMO)");
    });

    it("shows New Flight button for regular users", async () => {
        mockFlights();
        wrapper.vm.storage.loggedInUser.type = "ACTIVE";
        mountComponent();
        await flushPromises();

        expect(wrapper.findAll("a.btn")
            .filter(b => b.text() == "Crear vuelo")).toHaveLength(1);
        expect(wrapper.text()).not.toContain("Su almacenamiento está lleno.");
        expect(wrapper.text()).not.toContain("Póngase en contacto con AgroSmart para activar su cuenta.");
    });

    it("doesn't show New Flight button for demo users", async () => {
        mockFlights();
        wrapper.vm.storage.loggedInUser.type = "DEMO_USER";
        mountComponent();
        await flushPromises();

        expect(wrapper.text()).not.toContain("Crear vuelo");
        expect(wrapper.text()).toContain("No puede crear vuelos");
        expect(wrapper.text()).toContain("Póngase en contacto con AgroSmart para activar su cuenta.");
    });

    it("doesn't show New Flight button for deleted users", async () => {
        mockFlights();
        wrapper.vm.storage.loggedInUser.type = "DELETED";
        mountComponent();
        await flushPromises();

        expect(wrapper.text()).not.toContain("Crear vuelo");
        expect(wrapper.text()).toContain("No puede crear vuelos");
        expect(wrapper.text()).toContain("Póngase en contacto con AgroSmart para activar su cuenta.");
    });

    it("doesn't show New Flight button for users who are over disk quota", async () => {
        mockFlights();
        wrapper.vm.storage.loggedInUser.type = "ACTIVE";
        wrapper.vm.storage.loggedInUser.used_space = 200 * Math.pow(1024, 2); // 200GB used, 120GB max space
        mountComponent();
        await flushPromises();

        expect(wrapper.text()).not.toContain("Crear vuelo");
        expect(wrapper.text()).toContain("No puede crear vuelos");
        expect(wrapper.text()).not.toContain("Póngase en contacto con AgroSmart para activar su cuenta.");
        expect(wrapper.text()).toContain("Su almacenamiento está lleno.");
    });

    it("requests Flights as other user when impersonating", async () => {
        mockFlights();
        wrapper.vm.storage.otherUserPk = {
            pk: 123
        };
        mountComponent();
        await flushPromises();

        // 1st is /api/users, 2nd is /api/flights/uuid
        expect(mock.history.get[1].headers).toHaveProperty("TARGETUSER", 123);
    });

    it("respects impersonated User permissions (impersonated Demo = can't create Flights)", async () => {
        mockFlights();
        wrapper.vm.storage.loggedInUser.type = "ADMIN"; // current user is Admin...
        wrapper.vm.storage.otherUserPk = { // ...impersonating a Demo user
            pk: 123,
            type: "DEMO_USER"
        };
        mountComponent();
        await flushPromises();

        // When Admin impersonates Demo, no Create Flight button should appear
        expect(wrapper.findAll("a.btn")
            .filter(b => b.text() == "Crear vuelo")).toHaveLength(0);
        expect(wrapper.text()).toContain("No puede crear vuelos");
    });

    it("respects impersonated User permissions (impersonated Active = can create Flights)", async () => {
        mockFlights();
        wrapper.vm.storage.loggedInUser.type = "ADMIN"; // current user is Admin...
        wrapper.vm.storage.otherUserPk = { // ...impersonating an Active user
            pk: 123,
            type: "ACTIVE"
        };
        mountComponent();
        await flushPromises();

        // When Admin impersonates an Active user, the Create Flight button should appear
        expect(wrapper.findAll("a.btn")
            .filter(b => b.text() == "Crear vuelo")).toHaveLength(1);
        expect(wrapper.text()).not.toContain("No puede crear vuelos");
    });

    it("shows progress info on PROCESSING flights", async () => {
        mockFlights();
        mountComponent();
        await flushPromises();

        expect(wrapper.text()).toEqual(
            expect.stringMatching(/Example flight\s+\(40%\)\s+Some example annotations/));
        expect(wrapper.text()).toEqual(
            expect.stringMatching(/Completed flight\s+More example annotations/));
    });

    it("sends an update ping to API every second", async () => {
        mockFlights();
        mountComponent();
        await flushPromises();

        // 1st is /api/users, 2nd is /api/flights/uuid
        expect(mock.history.get).toHaveLength(2);
        jest.advanceTimersByTime(2000); // wait a bit
        await flushPromises();
        expect(mock.history.get.length).toBeGreaterThan(2);
    });
})