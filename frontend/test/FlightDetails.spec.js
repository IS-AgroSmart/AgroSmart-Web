import {
    createLocalVue,
    mount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import FlightDetails from 'components/FlightDetails.vue';

import {
    ListGroupPlugin,
    FormTextareaPlugin,
    FormPlugin,
    ProgressPlugin,
    ButtonPlugin,
    ImagePlugin,
    LinkPlugin,
} from 'bootstrap-vue';
import ReactiveStorage from "vue-reactive-localstorage";
import VueClipboard from 'vue-clipboard2';
import VueChatScroll from 'vue-chat-scroll';

const localVue = createLocalVue();
localVue.use(ListGroupPlugin);
localVue.use(FormTextareaPlugin);
localVue.use(FormPlugin);
localVue.use(ProgressPlugin);
localVue.use(ButtonPlugin);
localVue.use(ImagePlugin);
localVue.use(LinkPlugin);
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
localVue.prototype.$processingStepsODM = {
    10: "En cola",
    20: "Procesando",
    30: "Fallido",
    40: "Terminado",
    50: "Cancelado"
}
localVue.prototype.$processingStepsDjango = {
    "WAITING": "En cola",
    "PROCESSING": "Procesando",
    "ERROR": "Fallido",
    "COMPLETE": "Terminado",
    "CANCELED": "Cancelado"
  }
localVue.use(ReactiveStorage, {
    "token": "mytoken",
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
jest.useFakeTimers();

describe("Flight details component", () => {
    let wrapper, mock;

    const mountComponent = () => {
        wrapper = mount(FlightDetails, {
            localVue,
            stubs: ["b-tooltip", "router-link"],
            mocks: {
                $bvModal: {
                    msgBoxConfirm: jest.fn((title, config) => Promise.resolve(true))
                },
                $bvToast: {
                    toast: jest.fn(),
                },
                $route: {
                    params: {
                        uuid: "myuuid"
                    }
                },
                $router: {
                    replace: jest.fn(),
                }
            },
        });
    };

    const mockApi = (url, responseData, valid = true) => {
        if (valid) mock.onGet(url).reply(200, responseData);
        else mock.onGet(url).networkError();
    };

    const mockFlights = (valid = true) => mockApi(/api\/flights\/.+/, {
        uuid: "processingflightuuid",
        camera: "RGB",
        processing_time: 6000,
        state: "PROCESSING",
        date: "2020-01-01",
        name: "Example flight",
        annotations: "Some example annotations",
        is_demo: false,
    }, valid);
    const mockCompleteFlight = (demo = false) => mockApi(/api\/flights\/.+/, {
        uuid: "uuid",
        camera: "RGB",
        processing_time: 6000,
        state: "COMPLETE",
        date: "2020-01-01",
        name: "Example flight",
        annotations: "Some example annotations",
        is_demo: demo,
    }, true);
    const mockConsole = (valid = true) => mockApi(/nodeodm\/task\/[^/]+\/output/, ["line 1", "line 2"], valid);
    const mockInfo = (valid = true) => mockApi(/nodeodm\/task\/[^/]+\/info/, {
        status: {
            code: 20
        },
        processingTime: 6000,
        progress: 42.42
    }, valid);
    const mockCompleteInfo = (valid = true) => mockApi(/nodeodm\/task\/[^/]+\/info/, {
        status: {
            code: 40
        },
        processingTime: 6000,
        progress: 100
    }, valid);

    const mockAllApisOk = () => {
        mockFlights();
        mockConsole();
        mockInfo();
    };
    const mockAllApisComplete = (demo = false) => {
        mockCompleteFlight(demo);
        mockConsole();
        mockCompleteInfo();
    };
    const mockPreviewUrl = () => mock.onGet(/api\/preview\/.+/).reply(200, {
        url: "http://example.com/image.png"
    });

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

    it("sends auth data to /nodeodm", async () => {
        mockAllApisOk();
        mountComponent();
        await flushPromises();

        expect(mock.history.get[2].headers).toHaveProperty("Authorization", "Token mytoken");
        expect(mock.history.get[3].headers).toHaveProperty("Authorization", "Token mytoken");
    })

    it("sets error if unable to get flight info", async () => {
        mockFlights(false);
        mockConsole();
        mockInfo();
        mountComponent();
        await flushPromises();

        expect(wrapper.vm.error).toBeTruthy();
    })

    it("sends admin impersonation data if set", async () => {
        mockAllApisOk();
        wrapper.vm.storage.otherUserPk = {
            pk: 123
        };
        mountComponent();
        await flushPromises();

        // api/users, api/flights/???, nodeodm/task/???/info, nodeodm/task/???/console
        expect(mock.history.get).toHaveLength(4);
        expect(mock.history.get[1].headers).toHaveProperty("TARGETUSER", 123);
        expect(mock.history.get[2].headers).toHaveProperty("TARGETUSER", 123);
        expect(mock.history.get[3].headers).toHaveProperty("TARGETUSER", 123);
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

    it("shows Cancel button when flight processing", async () => {
        mockAllApisOk();
        mountComponent();
        await flushPromises();

        expect(wrapper.text()).toContain("Cancelar");
        expect(wrapper.text()).not.toContain("Eliminar");
    });

    it("sends cancel request on processing flight", async () => {
        mockAllApisOk();
        mountComponent();
        await flushPromises();
        mock.onPost("nodeodm/task/cancel").reply(200);

        await wrapper.vm.cancelFlight();
        await flushPromises();

        expect(mock.history.post.length).toBeGreaterThan(0);
        expect(JSON.parse(mock.history.post[0].data)).toHaveProperty("uuid", "processingflightuuid");
        expect(mock.history.post[0].headers).toHaveProperty("Authorization", "Token mytoken");
        expect(wrapper.vm.$bvModal.msgBoxConfirm).toHaveBeenCalledWith(
            "¿Realmente desea cancelar el procesamiento del vuelo?", expect.any(Object));
    });

    it("shows Delete button when flight complete processing", async () => {
        mockAllApisComplete();
        mockPreviewUrl();
        mountComponent();
        await flushPromises();

        expect(wrapper.text()).not.toContain("Cancelar");
        expect(wrapper.text()).toContain("Eliminar");
    });

    it("sends DELETE request on complete flight", async () => {
        mockAllApisComplete();
        mockPreviewUrl();
        mountComponent();
        await flushPromises();
        mock.onDelete(/api\/flights\/.+/).reply(200);

        await wrapper.vm.deleteFlight();
        await flushPromises();

        expect(mock.history.delete.length).toBeGreaterThan(0);
        expect(wrapper.vm.$bvModal.msgBoxConfirm).toHaveBeenCalledWith(
            "Este vuelo podrá ser recuperado durante 30 días.", expect.any(Object));
    });

    it("sends DELETE request on demo flight", async () => {
        mockAllApisComplete(true);
        mockPreviewUrl();
        mountComponent();
        await flushPromises();
        mock.onDelete(/api\/flights\/.+/).reply(200);

        await wrapper.vm.deleteFlight();
        await flushPromises();

        expect(mock.history.delete).toHaveLength(1);
        expect(wrapper.vm.$bvModal.msgBoxConfirm).toHaveBeenCalledWith(
            "Este vuelo no podrá ser recuperado.", expect.any(Object));
    });

    it("sends DELETE request as other user", async () => {
        mockAllApisComplete();
        mockPreviewUrl();
        wrapper.vm.storage.otherUserPk = {
            pk: 123
        };
        mountComponent();
        await flushPromises();
        mock.onDelete(/api\/flights\/.+/).reply(200);

        await wrapper.vm.deleteFlight();
        await flushPromises();

        expect(mock.history.delete[0].headers).toHaveProperty("TARGETUSER", 123);
    });

    it("shows toast if DELETE request fails", async () => {
        mockAllApisComplete();
        mockPreviewUrl();
        mountComponent();
        await flushPromises();
        mock.onDelete(/api\/flights\/.+/).networkError();

        let deleteButton = wrapper.findAll("button").filter(b => b.text() == "Eliminar");
        await deleteButton.trigger("click");
        await flushPromises();

        expect(mock.history.delete.length).toBeGreaterThan(0);
        expect(wrapper.vm.$bvToast.toast).toHaveBeenCalledWith(
            expect.stringMatching(/Error/), expect.any(Object));
    });

    it("shows tooltip and starts timer when copy has error", async () => {
        mockAllApisOk();
        mountComponent();
        await flushPromises();

        let copyButton = wrapper.findAll("button").filter(b => b.text() == "Copiar");
        await copyButton.trigger("click");
        await flushPromises();

        expect(wrapper.text()).toContain("No se pudo copiar el texto");
        expect(window.setTimeout).toHaveBeenCalled();
    });

    it("shows tooltip and starts timer when copy successful", async () => {
        mockAllApisOk();
        mountComponent();
        await flushPromises();

        wrapper.vm.onCopySuccess();
        await flushPromises();

        expect(wrapper.text()).toContain("Contenido copiado");
        expect(window.setTimeout).toHaveBeenCalled();
    });

    it("hides tooltip after some time", async () => {
        mockAllApisOk();
        mountComponent();
        await flushPromises();

        wrapper.vm.onCopySuccess();
        await flushPromises();

        expect(wrapper.text()).toContain("Contenido copiado");
        expect(window.setTimeout).toHaveBeenCalled();
        jest.advanceTimersByTime(1000);
        await flushPromises();
        await wrapper.vm.$nextTick();
    });
})