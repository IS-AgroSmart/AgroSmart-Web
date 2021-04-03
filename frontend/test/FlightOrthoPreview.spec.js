import {
    createLocalVue,
    shallowMount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import FlightOrthoPreview2 from 'components/FlightOrthoPreview2.vue';

import BootstrapVue from 'bootstrap-vue';
import ReactiveStorage from "vue-reactive-localstorage";
//import VueLayers from "vuelayers";

const localVue = createLocalVue();
localVue.use(BootstrapVue);
localVue.prototype.$isLoggedIn = () => true;
localVue.use(ReactiveStorage, {
    "token": "mytoken",
    "isAdmin": false,
    "otherUserPk": 0,
    "loggedInUser": {},
});
//localVue.use(VueLayers);

import axios from 'axios'
import MockAdapter from 'axios-mock-adapter';

jest.useFakeTimers();

describe('Login component', () => {
    let wrapper, mock;

    const MapViewStub = {
        render: () => {},
        $view: {
            fit: jest.fn(),
        },
    };

    function mountComponent() {
        wrapper = shallowMount(FlightOrthoPreview2, {
            localVue,
            stubs: {
                "model-obj": MapViewStub,
                "vl-map": MapViewStub,
                "vl-layer-image": MapViewStub,
                "vl-source-image-wms": MapViewStub,
                "vl-source-xyz": MapViewStub,
                "vl-layer-tile": MapViewStub,
                "vl-view": MapViewStub,
            },
            mocks: {
                $route: {
                    params: {
                        uuid: "myuuid"
                    }
                },
            },
        });
    }

    function _mockGet(url, response, valid = true) {
        if (valid) mock.onGet(url).reply(200, response);
        else mock.onGet(url).networkError();
    }

    function mockAllOk() {
        _mockGet("api/flights/myuuid", {
            uuid: "myuuid",
            name: "Flight Name"
        });
        _mockGet("/api/preview/myuuid", {
            srs: "EPSG:4326",
            bbox: {
                xmin: 0,
                xmax: 1,
                ymin: 0,
                ymax: 1
            },
        });
    }

    beforeEach(() => {
        mock = new MockAdapter(axios);
    });

    afterEach(function () {
        mock.restore();
    });

    it("calls the flight info APIs", async () => {
        mockAllOk();
        mountComponent();
        await flushPromises();

        // 1st is /api/users, 2nd is /api/flights/uuid, 3rd is /api/preview/uuid
        expect(mock.history.get).toHaveLength(3);
    });

    it("calls info API as other user", async () => {
        wrapper.vm.storage.otherUserPk = {
            pk: 123
        };
        mockAllOk();
        mountComponent();
        await flushPromises();

        // get[0] is /api/users
        expect(mock.history.get[1].headers).toHaveProperty("TARGETUSER", 123);
    });

    it("shows error if first API call fails", async () => {
        wrapper.vm.storage.otherUserPk = {
            pk: 123
        };
        _mockGet("api/flights/myuuid", null, false);
        mountComponent();
        await flushPromises();

        // TODO: show error message?
        expect(wrapper.vm.error).toBeTruthy();
    });

    /*it("sets map extent after 1 second", async () => {
        mockAllOk();
        mountComponent();
        await flushPromises();

        wrapper.vm.$refs.mapView = {
            $view: {
                fit: jest.fn(),
            },
        };
        jest.advanceTimersByTime(1500);
        expect(setTimeout).toHaveBeenCalledTimes(1);
        expect(setTimeout).toHaveBeenLastCalledWith(expect.any(Function), 1000);
        expect(wrapper.vm.$refs.mapView.$view.fit).toHaveBeenCalled();
    });*/
});