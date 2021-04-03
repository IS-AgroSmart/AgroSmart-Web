import {
    createLocalVue,
    mount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import FlightResults from 'components/FlightResults.vue';

import {
    ButtonPlugin,
    CardPlugin,
    AlertPlugin,
    FormPlugin,
    FormGroupPlugin,
    FormCheckboxPlugin,
    LayoutPlugin,
} from 'bootstrap-vue'
import ReactiveStorage from "vue-reactive-localstorage";

const localVue = createLocalVue();
localVue.use(ButtonPlugin);
localVue.use(CardPlugin);
localVue.use(AlertPlugin);
localVue.use(FormPlugin);
localVue.use(FormCheckboxPlugin);
localVue.use(FormGroupPlugin);
localVue.use(LayoutPlugin);
localVue.prototype.$isLoggedIn = () => true;
localVue.use(ReactiveStorage, {
    "token": "",
    "isAdmin": false,
    "otherUserPk": 0,
    "loggedInUser": {
        type: "DEMO_USER",
        username: "admin"
    }
});


import axios from 'axios'
import MockAdapter from 'axios-mock-adapter';

describe("Flight results component", () => {
    let wrapper, mock;
    window.URL.createObjectURL = jest.fn();

    const mountComponent = () => {
        wrapper = mount(FlightResults, {
            localVue,
            mocks: {
                $route: {
                    params: {
                        uuid: "myuuid"
                    }
                }
            },
        });
    };

    function mockSuccessful() {
        mock.onGet(/api\/flights\/.+/).reply(200, {
            uuid: "flightuuid",
            name: "Flight Name"
        });
    }

    function mockError() {
        mock.onGet(/api\/flights\/.+/).networkError();
    }

    beforeEach(() => {
        mock = new MockAdapter(axios);
        mock.onGet("api/users").replyOnce(200, [{
            id: 1,
            username: "admin"
        }]);
    });

    afterEach(function () {
        mock.restore();
        wrapper.vm.storage.otherUserPk = 0;
        window.URL.createObjectURL.mockReset();
    });

    it("calls API and fills flight info", async () => {
        mockSuccessful();
        mountComponent();
        await flushPromises();

        expect(wrapper.text()).toContain("Flight Name");
        // 1st is /api/users, 2nd is /api/flights/uuid
        expect(mock.history.get).toHaveLength(2);
        expect(mock.history.get[1].url).toContain("/flights/myuuid");
        expect(wrapper.find(".alert").exists()).toBe(false);
    });

    it("calls API as other user", async () => {
        wrapper.vm.storage.otherUserPk = {
            pk: 123
        };
        mockSuccessful();
        mountComponent();
        await flushPromises();

        // get[0] is /api/users
        expect(mock.history.get[1].headers).toHaveProperty("TARGETUSER", 123);
    });

    it("shows alert if API call fails", async () => {
        mockError();
        mountComponent();
        await flushPromises();

        expect(wrapper.vm.error).toBeTruthy();
        expect(wrapper.find(".alert").exists()).toBe(true);
    })
})