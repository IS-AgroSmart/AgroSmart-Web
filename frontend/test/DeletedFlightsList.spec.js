import {
    createLocalVue,
    mount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import DeletedFlights from 'components/DeletedFlights.vue';

import { ButtonPlugin, CardPlugin, AlertPlugin } from 'bootstrap-vue';
import ReactiveStorage from "vue-reactive-localstorage";

const localVue = createLocalVue();
localVue.use(ButtonPlugin);
localVue.use(CardPlugin);
localVue.use(AlertPlugin);
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

describe("Deleted flights component", () => {
    let wrapper, mock;

    const mountComponent = () => {
        wrapper = mount(DeletedFlights, {
            localVue,
            mocks: {
                $bvModal: {
                    msgBoxConfirm: jest.fn().mockResolvedValue(true),
                },
                $bvToast: {
                    toast: jest.fn(),
                }
            }
        });
    };

    const mockApi = (url, responseData, valid = true) => {
        if (valid) mock.onGet(url).reply(200, responseData);
        else mock.onGet(url).networkError();
    };

    const mockFlights = (valid = true) => mockApi("api/flights/deleted", [{
        uuid: "uuid2",
        camera: "RGB",
        processing_time: 6000,
        state: "COMPLETE",
        date: "2020-01-01",
        name: "Completed flight",
        annotations: "Example annotations",
        nodeodm_info: {
            progress: 100,
        },
        is_demo: false,
    }, {
        uuid: "uuid3",
        camera: "RGB",
        processing_time: 8000,
        state: "COMPLETE",
        date: "2020-01-01",
        name: "Another completed flight",
        annotations: "More example annotations",
        nodeodm_info: {
            progress: 100,
        },
        is_demo: false,
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

        expect(wrapper.text()).toContain("Completed flight");
        expect(wrapper.text()).toContain("Another completed flight");

        expect(mock.history.get.length).toBe(1);
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

    it("shows Restore and Delete button on all flights", async () => {
        mockFlights();
        mountComponent();
        await flushPromises();

        let buttons = wrapper.findAll(".btn.btn-success").filter(b => b.text() == "Restaurar");
        expect(buttons).toHaveLength(2);
        buttons = wrapper.findAll(".btn.btn-danger").filter(b => b.text() == "Eliminar");
        expect(buttons).toHaveLength(2);
    });

    it("sends a DELETE request when the Delete button is clicked", async () => {
        mockFlights();
        mountComponent();
        await flushPromises();
        mock.onDelete(/api\/flights\/.+/).reply(204);

        let button = wrapper.findAll(".btn.btn-danger").filter(b => b.text() == "Eliminar").at(0);
        expect(mock.history.delete).toHaveLength(0);
        await button.trigger("click");
        await flushPromises();
        expect(mock.history.delete).toHaveLength(1);
        expect(wrapper.vm.$bvModal.msgBoxConfirm).toHaveBeenCalledWith(expect.any(String), expect.any(Object));
        expect(wrapper.vm.$bvToast.toast).not.toHaveBeenCalled();
    });

    it("shows a toast when Delete request fails", async () => {
        mockFlights();
        mountComponent();
        await flushPromises();
        mock.onDelete(/api\/flights\/.+/).reply(500);

        let button = wrapper.findAll(".btn.btn-danger").filter(b => b.text() == "Eliminar").at(0);
        await button.trigger("click");
        await flushPromises();
        expect(mock.history.delete).toHaveLength(1);
        expect(wrapper.vm.$bvToast.toast).toHaveBeenCalled();
    });

    it("sends a DELETE request as other user", async () => {
        mockFlights();
        wrapper.vm.storage.otherUserPk = {
            pk: 123
        };
        mountComponent();
        await flushPromises();
        mock.onDelete(/api\/flights\/.+/).reply(204);

        let button = wrapper.findAll(".btn.btn-danger").filter(b => b.text() == "Eliminar").at(0);
        await button.trigger("click");
        await flushPromises();
        expect(mock.history.delete[0].headers).toHaveProperty("TARGETUSER", 123);
    });

    it("doesn't send a DELETE request when Delete request aborted", async () => {
        mockFlights();
        mountComponent();
        await flushPromises();
        mock.onDelete(/api\/flights\/.+/).reply(204);
        wrapper.vm.$bvModal.msgBoxConfirm = jest.fn().mockResolvedValue(false);

        let button = wrapper.findAll(".btn.btn-danger").filter(b => b.text() == "Eliminar").at(0);
        await button.trigger("click");
        await flushPromises();
        expect(mock.history.delete).toHaveLength(0);
        expect(wrapper.vm.$bvModal.msgBoxConfirm).toHaveBeenCalled();
        expect(wrapper.vm.$bvToast.toast).not.toHaveBeenCalled();
    });

    it("sends a restore request when the Restore button is clicked", async () => {
        mockFlights();
        mountComponent();
        await flushPromises();
        mock.onPatch(/api\/flights\/.+/).reply(200);

        let button = wrapper.findAll(".btn.btn-success").filter(b => b.text() == "Restaurar").at(0);
        expect(mock.history.patch).toHaveLength(0);
        await button.trigger("click");
        await flushPromises();
        expect(mock.history.patch).toHaveLength(1);
        // Restore doesn't show confirm box!
        expect(wrapper.vm.$bvModal.msgBoxConfirm).not.toHaveBeenCalled();
        expect(wrapper.vm.$bvToast.toast).not.toHaveBeenCalled();
    });

    it("shows a toast when Restore request fails", async () => {
        mockFlights();
        mountComponent();
        await flushPromises();
        mock.onPatch(/api\/flights\/.+/).reply(500);

        let button = wrapper.findAll(".btn.btn-success").filter(b => b.text() == "Restaurar").at(0);
        await button.trigger("click");
        await flushPromises();
        expect(mock.history.patch).toHaveLength(1);
        expect(wrapper.vm.$bvToast.toast).toHaveBeenCalled();
    });

    it("sends a restore request as other user", async () => {
        mockFlights();
        wrapper.vm.storage.otherUserPk = {
            pk: 123
        };
        mountComponent();
        await flushPromises();
        mock.onPatch(/api\/flights\/.+/).reply(204);

        let button = wrapper.findAll(".btn.btn-success").filter(b => b.text() == "Restaurar").at(0);
        await button.trigger("click");
        await flushPromises();
        expect(mock.history.patch[0].headers).toHaveProperty("TARGETUSER", 123);
    });
})