import {
    createLocalVue,
    mount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import FlightDetails from 'components/Project.vue';

import {
    ButtonPlugin,
    CardPlugin,
    AlertPlugin,
    SkeletonPlugin,
    LayoutPlugin   
} from 'bootstrap-vue'
import ReactiveStorage from "vue-reactive-localstorage";

const localVue = createLocalVue();
localVue.use(ButtonPlugin);
localVue.use(CardPlugin);
localVue.use(AlertPlugin);
localVue.use(SkeletonPlugin);
localVue.use(LayoutPlugin);
localVue.prototype.$isLoggedIn = () => true;
localVue.use(ReactiveStorage, {
    "token": "",
    "isAdmin": false,
    "otherUserPk": 0,
    "loggedInUser": {
        type: "DEMO_USER",
        used_space: 50 * Math.pow(1024, 2),
        maximum_space: 120 * Math.pow(1024, 2)
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

        expect(mock.history.get).toHaveLength(2); // 1 call to /api/users, 1 call to /api/projects
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
        expect(wrapper.text()).toContain("Póngase en contacto con AgroSmart para activar su cuenta.");
    });

    it("doesn't show New Project button for deleted users", async () => {
        mockProjects();
        wrapper.vm.storage.loggedInUser.type = "DELETED";
        mountComponent();
        await flushPromises();

        expect(wrapper.text()).not.toContain("Crear proyecto");
        expect(wrapper.text()).toContain("No puede crear proyectos");
        expect(wrapper.text()).toContain("Póngase en contacto con AgroSmart para activar su cuenta.");
    });


    it("doesn't show New Project button for users who are over disk quota", async () => {
        mockProjects();
        wrapper.vm.storage.loggedInUser.type = "ACTIVE";
        wrapper.vm.storage.loggedInUser.used_space = 200 * Math.pow(1024, 2); // 200GB used, 120GB max space
        mountComponent();
        await flushPromises();

        expect(wrapper.text()).not.toContain("Crear proyecto");
        expect(wrapper.text()).toContain("No puede crear proyectos");
        expect(wrapper.text()).not.toContain("Póngase en contacto con AgroSmart para activar su cuenta.");
        expect(wrapper.text()).toContain("Su almacenamiento está lleno.");
    });

    it("requests Projects as other user when impersonating", async () => {
        mockProjects();
        wrapper.vm.storage.otherUserPk = {
            pk: 123
        };
        mountComponent();
        await flushPromises();

        expect(mock.history.get[1].headers).toHaveProperty("TARGETUSER", 123); // get[0] is a request to /api/users
    });

    it("respects impersonated User permissions (impersonated Demo = can't create Projects)", async () => {
        mockProjects();
        wrapper.vm.storage.loggedInUser.type = "ADMIN"; // current user is Admin...
        wrapper.vm.storage.otherUserPk = { // ...impersonating a Demo user
            pk: 123,
            type: "DEMO_USER"
        };
        mountComponent();
        await flushPromises();

        // When Admin impersonates Demo, no Create Project button should appear
        expect(wrapper.findAll("a.btn")
            .filter(b => b.text() == "Crear proyecto")).toHaveLength(0);
        expect(wrapper.text()).toContain("No puede crear proyectos");
    });

    it("respects impersonated User permissions (impersonated Active = can create Projects)", async () => {
        mockProjects();
        wrapper.vm.storage.loggedInUser.type = "ADMIN"; // current user is Admin...
        wrapper.vm.storage.otherUserPk = { // ...impersonating an Active user
            pk: 123,
            type: "ACTIVE"
        };
        mountComponent();
        await flushPromises();

        // When Admin impersonates an Active user, the Create Project button should appear
        expect(wrapper.findAll("a.btn")
            .filter(b => b.text() == "Crear proyecto")).toHaveLength(1);
        expect(wrapper.text()).not.toContain("No puede crear proyectos");
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
        expect(wrapper.vm.$bvToast.toast).toHaveBeenCalled();
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