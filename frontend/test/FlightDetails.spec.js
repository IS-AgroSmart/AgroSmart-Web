import {
    createLocalVue,
    mount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import FlightDetails from 'components/FlightDetails.vue';

import BootstrapVue from 'bootstrap-vue';
import ReactiveStorage from "vue-reactive-localstorage";
import VueClipboard from 'vue-clipboard2';
import VueChatScroll from 'vue-chat-scroll';

const localVue = createLocalVue();
localVue.use(BootstrapVue);
localVue.prototype.$isLoggedIn = () => true;
localVue.prototype.$cameras = [{
        text: 'Micasense Rededge',
        value: "REDEDGE"
    },
    {
        text: 'RGB',
        value: "RGB"
    }
];
localVue.prototype.$processingSteps = {
    10: "En cola",
    20: "Procesando",
    30: "Fallido",
    40: "Terminado",
    50: "Cancelado"
}
localVue.use(ReactiveStorage, {
    "token": "",
    "isAdmin": false,
    "otherUserPk": 0,
    "loggedInUser": {}
});
const moment = require('moment');
require('moment/locale/es');
localVue.use(require('vue-moment'), {
    moment
});
localVue.use(VueClipboard);
localVue.use(VueChatScroll);

import axios from 'axios'
import MockAdapter from 'axios-mock-adapter';

const mutationObserverMock = jest.fn(function MutationObserver(callback) {
    this.observe = jest.fn();
    this.disconnect = jest.fn();
    // Optionally add a trigger() method to manually trigger a change
    this.trigger = (mockedMutationsList) => {
        callback(mockedMutationsList, this);
    };
});
global.MutationObserver = mutationObserverMock;

describe("User details component", () => {
    let wrapper, mock;

    const mountComponent = () => {
        wrapper = mount(FlightDetails, {
            localVue,
            stubs: ["b-tooltip"],
            mocks: {
                $bvmodal: {
                    msgBoxConfirm: jest.fn((title, config) => Promise.resolve(true))
                },
                $route: {
                    params: {
                        uuid: "myuuid"
                    }
                }
            },
        });
    };

    const mockApi = (url, responseData, valid = true) => {
        if (valid) mock.onGet(url).reply(200, responseData);
        else mock.onGet(url).networkError();
    };

    const mockFlights = (valid = true) => mockApi(/api\/flights\/.+/, {
        uuid: "uuid",
        camera: "RGB",
        processing_time: 6000,
        state: "PROCESSING",
        date: "2020-01-01",
        name: "Example flight",
        annotations: "Some example annotations"
    }, valid);
    const mockConsole = (valid = true) => mockApi(/nodeodm\/task\/[^\/]+\/output/, ["line 1", "line 2"], valid);
    const mockInfo = (valid = true) => mockApi(/nodeodm\/task\/[^\/]+\/info/, {
        status: {
            code: 20
        },
        processingTime: 6000,
        progress: 42.42
    }, valid);

    const mockAllApisOk = () => {
        mockFlights();
        mockConsole();
        mockInfo();
    };

    beforeEach(() => {
        mock = new MockAdapter(axios);
    });

    afterEach(function () {
        mock.restore();
        wrapper.vm.storage.otherUserPk = 0;
    });

    it("shows flight info", async () => {
        mockAllApisOk();
        mountComponent();
        await flushPromises();

        expect(wrapper.text()).toContain("Example flight");
        expect(wrapper.text()).toContain("Some example annotations");
        expect(wrapper.text()).toContain("Procesando");
    });

    it("sends admin impersonation data if set", async () => {
        mockAllApisOk();
        wrapper.vm.storage.otherUserPk = {
            pk: 123
        };
        mountComponent();
        await flushPromises();

        expect(mock.history.get[0].headers).toHaveProperty("TARGETUSER", 123);
    });

    it("doesn't send admin data if not set", async () => {
        mockAllApisOk();
        mountComponent();
        await flushPromises();

        expect(mock.history.get[0].headers).not.toHaveProperty("TARGETUSER");
    });

    it("sets error info if console endpoint fails", async () => {
        mockFlights();
        mockConsole(false);
        mockInfo();
        mountComponent();
        await flushPromises();

        expect(wrapper.vm.error).not.toBeNull();
    });
})