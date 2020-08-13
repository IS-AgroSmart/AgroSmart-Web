import {
    createLocalVue,
    mount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import FlightDetails from 'components/Project.vue';

import { ButtonPlugin, CardPlugin, AlertPlugin } from 'bootstrap-vue'
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

describe("Project list component", () => {
    let wrapper, mock;

    const mountComponent = () => {
        wrapper = mount(FlightDetails, {
            localVue,
            mocks: {
                $bvModal: {
                    msgBoxConfirm: jest.fn().mockResolvedValue(true),
                },
                $bvToast: {
                    toast: jest.fn(),
                },
                $router: {
                    push: jest.fn(),
                },
            },
        });
    };

    const mockApi = (url, responseData, valid = true) => {
        if (valid) mock.onGet(url).reply(200, responseData);
        else mock.onGet(url).networkError();
    };

    const mockProjects = (valid = true) => mockApi("api/projects", [{
        uuid: "uuid",
        name: "Example project",
        description: "Some example annotations",
        is_demo: false,
    }, {
        uuid: "uuid2",
        name: "Another demo project",
        description: "More example annotations",
        is_demo: true,
    }], valid);

    beforeEach(() => {
        mock = new MockAdapter(axios);
    });

    afterEach(function () {
        mock.restore();
        wrapper.vm.storage.otherUserPk = 0;
    });

    it("shows a list with projects", async () => {
        mockProjects();
        mountComponent();
        await flushPromises();

        expect(wrapper.text()).toContain("Example project");
        expect(wrapper.text()).toContain("Some example annotations");
        expect(wrapper.text()).toContain("Another demo project");
        expect(wrapper.text()).toContain("Example project");

        expect(mock.history.get.length).toBe(1);
    });

    it("correctly identifies demo projects", async () => {
        mockProjects();
        mountComponent();
        await flushPromises();

        expect(wrapper.text()).toContain("Another demo project (DEMO)");
        expect(wrapper.text()).not.toContain("Example project (DEMO)");
    });

    it("shows New Project button for regular users", async () => {
        mockProjects();
        wrapper.vm.storage.loggedInUser.type = "ACTIVE";
        mountComponent();
        await flushPromises();

        expect(wrapper.text()).toContain("Crear proyecto");
    });

    it("doesn't show New Project button for demo users", async () => {
        mockProjects();
        wrapper.vm.storage.loggedInUser.type = "DEMO_USER";
        mountComponent();
        await flushPromises();

        expect(wrapper.text()).not.toContain("Crear proyecto");
        expect(wrapper.text()).toContain("No puede crear proyectos");
    });

    it("doesn't show New Project button for deleted users", async () => {
        mockProjects();
        wrapper.vm.storage.loggedInUser.type = "DELETED";
        mountComponent();
        await flushPromises();

        expect(wrapper.text()).not.toContain("Crear proyecto");
        expect(wrapper.text()).toContain("No puede crear proyectos");
    });

    it("requests Projects as other user when impersonating", async () => {
        mockProjects();
        wrapper.vm.storage.otherUserPk = {
            pk: 123
        };
        mountComponent();
        await flushPromises();

        expect(mock.history.get[0].headers).toHaveProperty("TARGETUSER", 123);;
    });

    it("shows a Show map button on all projects", async () => {
        mockProjects();
        mountComponent();
        await flushPromises();

        let buttons = wrapper.findAll(".btn.btn-primary").filter(b => b.text() == "Ver mapa");
        expect(buttons).toHaveLength(2);
    });

    it("shows a Delete button on all projects", async () => {
        mockProjects();
        mountComponent();
        await flushPromises();

        let buttons = wrapper.findAll(".btn.btn-danger").filter(b => b.text() == "Eliminar");
        expect(buttons).toHaveLength(2);
    });

    it("sends a DELETE request when the Delete button is clicked", async () => {
        mockProjects();
        mountComponent();
        await flushPromises();
        mock.onDelete(/api\/projects\/.+/).reply(204);

        let button = wrapper.findAll(".btn.btn-danger").filter(b => b.text() == "Eliminar").at(0);
        expect(mock.history.delete).toHaveLength(0);
        await button.trigger("click");
        await flushPromises();
        expect(mock.history.delete).toHaveLength(1);
        expect(wrapper.vm.$bvModal.msgBoxConfirm).toHaveBeenCalledWith(expect.any(String), expect.any(Object));
        expect(wrapper.vm.$bvToast.toast).not.toHaveBeenCalled();
    });

    it("shows a toast when Delete request fails", async () => {
        mockProjects();
        mountComponent();
        await flushPromises();
        mock.onDelete(/api\/projects\/.+/).reply(500);

        let button = wrapper.findAll(".btn.btn-danger").filter(b => b.text() == "Eliminar").at(0);
        await button.trigger("click");
        await flushPromises();
        expect(mock.history.delete).toHaveLength(1);
        expect(wrapper.vm.$bvToast.toast).toHaveBeenCalled();
    });

    it("sends a DELETE request as other user", async () => {
        mockProjects();
        wrapper.vm.storage.otherUserPk = {
            pk: 123
        };
        mountComponent();
        await flushPromises();
        mock.onDelete(/api\/projects\/.+/).reply(204);

        let button = wrapper.findAll(".btn.btn-danger").filter(b => b.text() == "Eliminar").at(0);
        await button.trigger("click");
        await flushPromises();
        expect(mock.history.delete[0].headers).toHaveProperty("TARGETUSER", 123);
    });

    it("doesn't send a DELETE request when Delete request aborted", async () => {
        mockProjects();
        mountComponent();
        await flushPromises();
        mock.onDelete(/api\/projects\/.+/).reply(204);
        wrapper.vm.$bvModal.msgBoxConfirm = jest.fn().mockResolvedValue(false);

        let button = wrapper.findAll(".btn.btn-danger").filter(b => b.text() == "Eliminar").at(0);
        await button.trigger("click");
        await flushPromises();
        expect(mock.history.delete).toHaveLength(0);
        expect(wrapper.vm.$bvModal.msgBoxConfirm).toHaveBeenCalled();
        expect(wrapper.vm.$bvToast.toast).not.toHaveBeenCalled();
    });

    it("bumps to login page if not logged in already", async () => {
        localVue.prototype.$isLoggedIn = () => false;
        mountComponent();

        expect(wrapper.vm.$router.push).toHaveBeenCalledWith("/login");
    });
})