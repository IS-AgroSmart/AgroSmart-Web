import {
    createLocalVue,
    mount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import UploadImages from 'components/UploadImages.vue';

import {
    ButtonPlugin,
    CardPlugin,
    AlertPlugin,
    FormPlugin,
    FormGroupPlugin,
    FormFilePlugin,
    LayoutPlugin,
} from 'bootstrap-vue'
import ReactiveStorage from "vue-reactive-localstorage";

const localVue = createLocalVue();
localVue.use(ButtonPlugin);
localVue.use(CardPlugin);
localVue.use(AlertPlugin);
localVue.use(FormPlugin);
localVue.use(FormFilePlugin);
localVue.use(FormGroupPlugin);
localVue.use(LayoutPlugin);
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

describe("Upload images component", () => {
    let wrapper, mock;
    window.URL.createObjectURL = jest.fn();

    const mountComponent = () => {
        wrapper = mount(UploadImages, {
            localVue,
            mocks: {
                $route: {
                    params: {
                        uuid: "myuuid"
                    }
                },
                $router: {
                    replace: jest.fn(),
                },
            },
        });
    };

    function mockSuccessful(camera = "RGB") {
        mock.onGet(/api\/flights\/.+/).reply(200, {
            uuid: "flightuuid",
            name: "Flight Name",
            camera: camera,
        });
    }

    function mockError() {
        mock.onGet(/api\/flights\/.+/).networkError();
    }

    beforeEach(() => {
        mock = new MockAdapter(axios);

    });

    afterEach(function () {
        mock.restore();
        wrapper.vm.storage.otherUserPk = 0;
        window.URL.createObjectURL.mockReset();
    });

    it("calls API", async () => {
        mockSuccessful();
        mountComponent();
        await flushPromises();

        expect(mock.history.get).toHaveLength(1);
        expect(wrapper.vm.error).toBeFalsy();
    });

    it("calls API as other user", async () => {
        wrapper.vm.storage.otherUserPk = {
            pk: 123
        };
        mockSuccessful();
        mountComponent();
        await flushPromises();

        expect(mock.history.get[0].headers).toHaveProperty("TARGETUSER", 123);
    });

    it("shows alert if API call fails", async () => {
        mockError();
        mountComponent();
        await flushPromises();

        expect(wrapper.vm.error).toBeTruthy();
    });

    it("shows the correct file extensions", async () => {
        mockSuccessful("RGB");
        mountComponent();
        await flushPromises();
        expect(wrapper.text()).toContain("image/jpeg, image/png");

        mockSuccessful("REDEDGE");
        mountComponent();
        await flushPromises();
        expect(wrapper.text()).toContain("image/tiff");
    });

    it("formats single file name", async () => {
        mockSuccessful();
        mountComponent();
        await flushPromises();
        wrapper.vm.files = [new File([], "0001.jpg")];
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.formatNames(wrapper.vm.files)).toBe("0001.jpg");
    });

    it("formats file names", async () => {
        mockSuccessful();
        mountComponent();
        await flushPromises();
        wrapper.vm.files = [new File([], "0001.jpg"), new File([], "0002.jpg"), new File([], "0003.jpg")];
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.formatNames(wrapper.vm.files)).toBe("3 archivos seleccionados");
    });

    it("sends upload request", async () => {
        mockSuccessful();
        mock.onPost(/api\/upload-files\/myuuid/).reply(200);
        mountComponent();
        await flushPromises();
        wrapper.vm.files = [new File([], "0001.jpg"), new File([], "0002.jpg"), new File([], "0003.jpg")];

        wrapper.find("form").trigger("submit");
        await flushPromises();
        expect(wrapper.vm.$router.replace).toHaveBeenCalledWith(expect.objectContaining({
            name: "flightDetails",
            params: {
                uuid: "myuuid"
            }
        }));
    });

    it("uploads images as other user", async () => {
        mockSuccessful();
        wrapper.vm.storage.otherUserPk = {
            pk: 123
        }
        mock.onPost(/api\/upload-files\/myuuid/).reply(200);
        mountComponent();
        await flushPromises();

        wrapper.find("form").trigger("submit");
        await flushPromises();
        expect(mock.history.post[0].headers).toHaveProperty("TARGETUSER", 123);
    });

    it("shows error message when upload fails", async () => {
        mockSuccessful();
        mock.onPost(/api\/upload-files\/myuuid/).networkError();
        mountComponent();
        await flushPromises();

        wrapper.find("form").trigger("submit");
        await flushPromises();
        expect(wrapper.text()).toContain("Subida fallida");
    });
})