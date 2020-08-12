import {
    createLocalVue,
    mount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import FlightDetails from 'components/Flight.vue';

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
        type: "DEMO_USER"
    }
});


import axios from 'axios'
import MockAdapter from 'axios-mock-adapter';

jest.useFakeTimers();

describe("Flight list component", () => {
    let wrapper, mock;

    const mountComponent = () => {
        wrapper = mount(FlightDetails, {
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
    },{
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
    },{
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

        expect(mock.history.get.length).toBe(1);
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

        expect(wrapper.text()).toContain("Crear vuelo");
    });

    it("doesn't show New Flight button for demo users", async () => {
        mockFlights();
        wrapper.vm.storage.loggedInUser.type = "DEMO_USER";
        mountComponent();
        await flushPromises();

        expect(wrapper.text()).not.toContain("Crear vuelo");
        expect(wrapper.text()).toContain("No puede crear vuelos");
    });

    it("doesn't show New Flight button for deleted users", async () => {
        mockFlights();
        wrapper.vm.storage.loggedInUser.type = "DELETED";
        mountComponent();
        await flushPromises();

        expect(wrapper.text()).not.toContain("Crear vuelo");
        expect(wrapper.text()).toContain("No puede crear vuelos");
    });

    it("requests Flights as other user when impersonating", async () => {
        mockFlights();
        wrapper.vm.storage.otherUserPk = {
            pk: 123
        };
        mountComponent();
        await flushPromises();

        expect(mock.history.get[0].headers).toHaveProperty("TARGETUSER", 123);
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

        expect(mock.history.get.length).toBe(1);
        jest.advanceTimersByTime(2000);
        await flushPromises();
        expect(mock.history.get.length).toBeGreaterThan(1);
    });
})