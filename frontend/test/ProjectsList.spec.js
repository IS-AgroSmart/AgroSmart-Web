import {
    createLocalVue,
    mount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import FlightDetails from 'components/Project.vue';

import BootstrapVue from 'bootstrap-vue';
import ReactiveStorage from "vue-reactive-localstorage";

const localVue = createLocalVue();
localVue.use(BootstrapVue);
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

describe("User details component", () => {
    let wrapper, mock;

    const mountComponent = () => {
        wrapper = mount(FlightDetails, {
            localVue
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
    },{
        uuid: "uuid2",
        name: "Another project",
        description: "More example annotations",
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

        expect(mock.history.get.length).toBe(1);
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
})