import {
    createLocalVue,
    mount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import UploadGeotiff from 'components/UploadGeotiff.vue';

import BootstrapVue from 'bootstrap-vue';
import ReactiveStorage from "vue-reactive-localstorage";

const localVue = createLocalVue();
localVue.prototype.$isLoggedIn = () => true;
localVue.use(BootstrapVue);
localVue.use(ReactiveStorage, {
    "token": "newtoken",
    "isAdmin": false,
    "otherUserPk": 0,
    "loggedInUser": {
        pk: 246
    }
});

import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';

describe('GeoTIFF upload component', () => {
    let wrapper, mock;

    beforeEach(() => {
        wrapper = mount(UploadGeotiff, {
            localVue,
            mocks: {
                $route: {
                    params: {
                        uuid: "myuuid"
                    }
                }
            },
        });
        mock = new MockAdapter(axios);
    });

    afterEach(function () {
        mock.restore();
        wrapper.vm.storage.otherUserPk = 0;
    });

    it("sends API request", async () => {
        mock.onPost(/api\/uploads\/.+\/geotiff/).reply(200);

        wrapper.find('form').trigger('submit');
        await flushPromises();
        expect(wrapper.find('.alert-danger').exists()).toBeFalsy();
        expect(mock.history.post).toHaveLength(1);
        expect(mock.history.post[0].headers).toHaveProperty("Authorization", "Token newtoken");
    });

    it("sends API request as other user", async () => {
        mock.onPost(/api\/uploads\/.+\/geotiff/).reply(200);
        wrapper.vm.storage.otherUserPk = {
            pk: 123,
        }

        wrapper.find('form').trigger('submit');
        await flushPromises();
        expect(wrapper.find('.alert-danger').exists()).toBeFalsy();
        expect(mock.history.post).toHaveLength(1);
        expect(mock.history.post[0].headers).toHaveProperty("Authorization", "Token newtoken");
        expect(mock.history.post[0].headers).toHaveProperty("TARGETUSER", 123);
    });

    it("shows error message when upload fails", async () => {
        mock.onPost(/api\/uploads\/.+\/geotiff/).networkError();

        wrapper.find('form').trigger('submit');
        await flushPromises();
        expect(wrapper.find('.alert-danger').exists()).toBe(true);
        expect(wrapper.text()).toContain("Subida fallida");
    });

    it("shows error message when user is over quota", async () => {
        mock.onPost(/api\/uploads\/.+\/geotiff/).reply(402); // HTTP 402 Payment Required

        wrapper.find("form").trigger("submit");
        await flushPromises();
        expect(wrapper.find('.alert-danger').exists()).toBe(true);
        expect(wrapper.text()).toContain("Subida fallida");
        expect(wrapper.text()).toContain("Su almacenamiento está lleno.");
    });

    it("shows the correct message when no files selected", async () => {
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.anyFile).toBe(false);
        expect(wrapper.text()).toContain("¡No hay un ortomosaico seleccionado!");
    });

    it("shows the correct message when multiple files selected", async () => {
        wrapper.vm.file = new File([], "file.shp");
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.anyFile).toBe(true);
        expect(wrapper.text()).not.toContain("¡No hay un ortomosaico seleccionado!");
    });

    it("sends the file in API request", async () => {
        mock.onPost(/api\/uploads\/.+\/geotiff/).reply(200);
        wrapper.vm.file = new File(["file-contents"], "file.shp");
        await wrapper.vm.$nextTick();
        wrapper.find('form').trigger('submit');
        await flushPromises();

        expect(mock.history.post).toHaveLength(1);
    });

    it("generates the correct description message when file selected", async () => {
        wrapper.vm.file = new File(["file-contents"], "file.shp");
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.formatName([wrapper.vm.file])).toBe("file.shp");
    });

});