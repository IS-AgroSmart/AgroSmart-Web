import {
    createLocalVue,
    mount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import UploadShapefile from 'components/UploadShapefile.vue';

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

describe('Shapefile upload component', () => {
    let wrapper, mock;

    beforeEach(() => {
        wrapper = mount(UploadShapefile, {
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
        mock.onPost(/api\/uploads\/.+\/vectorfile/).reply(200);

        wrapper.find('form').trigger('submit');
        await flushPromises();
        expect(wrapper.find('.alert-danger').exists()).toBeFalsy();
        expect(mock.history.post).toHaveLength(1);
        expect(mock.history.post[0].headers).toHaveProperty("Authorization", "Token newtoken");
    });

    it("sends API request as other user", async () => {
        mock.onPost(/api\/uploads\/.+\/vectorfile/).reply(200);
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
        mock.onPost(/api\/uploads\/.+\/vectorfile/).networkError();

        wrapper.find('form').trigger('submit');
        await flushPromises();
        expect(wrapper.find('.alert-danger').exists()).toBe(true);
        expect(wrapper.text()).toContain("Subida fallida");
    });

    it("shows error message when user is over quota", async () => {
        mock.onPost(/api\/uploads\/.+\/vectorfile/).reply(402); // HTTP 402 Payment Required

        wrapper.find("form").trigger("submit");
        await flushPromises();
        expect(wrapper.find('.alert-danger').exists()).toBe(true);
        expect(wrapper.text()).toContain("Subida fallida");
        expect(wrapper.text()).toContain("Su almacenamiento está lleno.");
    });

    it("shows the correct message when wrong files selected", async () => {
        wrapper.vm.files = [new File([], "file.shp")];
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.validFiles).toBe(false);
        expect(wrapper.text()).toContain("Seleccione tres archivos con el mismo nombre y extensiones");
    });

    it("shows the correct message when multiple files selected", async () => {
        wrapper.vm.files = [new File([], "file.shp"), new File([], "file.shx"), new File([], "file.dbf")];
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.validFiles).toBe(true);
        expect(wrapper.text()).not.toContain("Seleccione tres archivos con el mismo nombre y extensiones");
    });

    it("sends the files in API request", async () => {
        mock.onPost(/api\/uploads\/.+\/shapefile/).reply(200);
        wrapper.vm.files = [new File(["file-contents"], "file.shp"), new File(["shx file"], "file.shx"), new File(["dbf file"], "file.dbf")];
        wrapper.vm.title = "awesome title";
        await wrapper.vm.$nextTick();
        wrapper.find('form').trigger('submit');
        await flushPromises();

        expect(mock.history.post).toHaveLength(1);
    });

    it("generates the correct description message when 3 files selected", async () => {
        wrapper.vm.files = [new File(["file-contents"], "file.shp"), new File(["shx file"], "file.shx"), new File(["dbf file"], "file.dbf")];
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.formatNames(wrapper.vm.files)).toBe("3 archivos seleccionados");
    });

    it("generates the correct description message when single file selected", async () => {
        wrapper.vm.files = [new File(["file-contents"], "file.shp")];
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.formatNames(wrapper.vm.files)).toBe("file.shp");
    });

    it("shows the correct message when KML and no files", async () => {
        wrapper.vm.files = [new File([], "file.kml")];
        wrapper.vm.datatype = "kml";
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.validFiles).toBe(false);
        expect(wrapper.text()).toContain("Escoja un único archivo .kml");
    });

    it("shows the correct message when KML and single file", async () => {
        wrapper.vm.datatype = "kml";
        wrapper.vm.files = new File([], "file.kml");
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.validFiles).toBe(true);
        expect(wrapper.text()).not.toContain("Seleccione un archivo con extensión .kml");
    });

    it("shows the correct message when wrong datatype", async () => {
        wrapper.vm.datatype = "foobar";
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.validFiles).toBe(false);
    });
});