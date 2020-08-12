import {
    createLocalVue,
    mount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import AdminHomepage from 'components/AdminHomepage.vue';
import AdminElementListPartial from 'components/AdminElementListPartial.vue';

import BootstrapVue from 'bootstrap-vue';
import ReactiveStorage from "vue-reactive-localstorage";

const localVue = createLocalVue();
localVue.use(BootstrapVue);
localVue.prototype.$isLoggedIn = () => true;
localVue.use(ReactiveStorage, {
    "token": "admintoken",
    "isAdmin": true,
    "otherUserPk": 0,
    "loggedInUser": {
        type: "ADMIN"
    }
});

import axios from 'axios'
import MockAdapter from 'axios-mock-adapter';

function withWrapperArray(wrapperArray) {
    return {
        childSelectorHasText: (selector, str) => wrapperArray.filter(i => i.find(selector).text().match(str)),
        hasText: (str) => wrapperArray.filter(i => i.text().match(str)),
    }
}

describe('Admin homepage component', () => {
    let wrapper, mock;

    beforeEach(() => {
        mock = new MockAdapter(axios);
        mock.onGet("api/flights").replyOnce(200, [{
            uuid: "uuid1",
            name: "Demo: Flight 1",
            is_demo: true,
            state: "COMPLETE"
        }, {
            uuid: "uuid2",
            name: "Not demo: Flight 2",
            is_demo: false,
            state: "COMPLETE"
        }, {
            uuid: "uuid3",
            name: "Not demo: Flight 3",
            is_demo: false,
            state: "COMPLETE"
        }, {
            uuid: "uuid4",
            name: "Processing: Flight 4",
            is_demo: false,
            state: "PROCESSING"
        }, {
            uuid: "uuid5",
            name: "Waiting: Flight 5",
            is_demo: false,
            state: "WAITING"
        }, {
            uuid: "uuid6",
            name: "Errored: Flight 6",
            is_demo: false,
            state: "ERROR"
        }, {
            uuid: "uuid7",
            name: "Canceled: Flight 7",
            is_demo: false,
            state: "CANCELED"
        }]);
        mock.onGet("api/projects").replyOnce(200, [{
            uuid: "uuid1",
            name: "Demo: Project 1",
            is_demo: true
        }, {
            uuid: "uuid2",
            name: "Not demo: Project 2",
            is_demo: false,
        }, {
            uuid: "uuid3",
            name: "Not demo: Project 3",
            is_demo: false,
        }]);
        mock.onGet("api/users").replyOnce(200, [{
            username: "admin",
            email: "admin@example.com"
        }, {
            username: "otheruser",
            email: "otheruser@gmail.com"
        }, {
            username: "newuser",
            email: "newuser@hotmail.com"
        }, ]);
        wrapper = mount(AdminHomepage, {
            localVue,
        });
    });

    afterEach(function () {
        mock.restore();
    });

    it("lists the admin's non-demo flights", async () => {
        await flushPromises();
        expect(mock.history.get[0].headers).toHaveProperty("Authorization", "Token admintoken")

        expect(wrapper.text()).toContain("Not demo: Flight 2");
        expect(wrapper.text()).toContain("Not demo: Flight 3");
    });

    it("shows buttons to convert flights to Demo", async () => {
        await flushPromises();

        // 6 buttons are Emulate button; User, Flight (x2) and Project (x2) dropdowns
        // 3 buttons are the User dropdown items
        // 2 buttons must be for the 2 non-demo COMPLETE flights
        // 1 button for the demo flight
        // 2 buttons for candidate demo proj, 1 for already demo proj
        let buttons = wrapper.findAll("button");
        expect(buttons).toHaveLength(15);
        expect(buttons.filter(b => b.text().includes("Not demo: Flight 2"))).toHaveLength(1);
        expect(buttons.filter(b => b.text().includes("Demo: Flight 1"))).toHaveLength(1);
        expect(buttons.filter(b => b.text().includes("Processing: Flight 4"))).toHaveLength(0);
        expect(buttons.filter(b => b.text().includes("Waiting: Flight 5"))).toHaveLength(0);
        expect(buttons.filter(b => b.text().includes("Errored: Flight 6"))).toHaveLength(0);
        expect(buttons.filter(b => b.text().includes("Canceled: Flight 7"))).toHaveLength(0);

        // 1 for users, 2 for flights, 2 for projects
        expect(wrapper.findAllComponents(AdminElementListPartial)).toHaveLength(5);
    });

    it("lists all user accounts", async () => {
        await flushPromises();

        expect(wrapper.text()).toContain("admin@example.com");
        expect(wrapper.text()).toContain("otheruser@gmail.com");
        expect(wrapper.text()).toContain("newuser@hotmail.com");
    });

    it("filters users by name", async () => {
        await flushPromises();
        wrapper.findAllComponents(AdminElementListPartial).at(0).vm.search = "user";

        await wrapper.vm.$nextTick(); // Allow for recomputing 
        expect(wrapper.text()).not.toContain("admin@example.com");
        expect(wrapper.text()).toContain("otheruser@gmail.com");
        expect(wrapper.text()).toContain("newuser@hotmail.com");
    });

    it("filters users by email", async () => {
        await flushPromises();
        wrapper.findAllComponents(AdminElementListPartial).at(0).vm.search = "example.com";

        await wrapper.vm.$nextTick(); // Allow for recomputing 
        expect(wrapper.text()).toContain("admin@example.com");
        expect(wrapper.text()).not.toContain("otheruser@gmail.com");
        expect(wrapper.text()).not.toContain("newuser@hotmail.com");
    });

    it("filters flights by name", async () => {
        await flushPromises();
        wrapper.findAllComponents(AdminElementListPartial).at(1).vm.search = "flight 2";

        await wrapper.vm.$nextTick();
        expect(wrapper.text()).toContain("Not demo: Flight 2");
        expect(wrapper.text()).not.toContain("Not demo: Flight 3");
    });

    it("filters projects by name", async () => {
        await flushPromises();
        wrapper.findAllComponents(AdminElementListPartial).at(3).vm.search = "project 2";

        await wrapper.vm.$nextTick();
        expect(wrapper.text()).toContain("Not demo: Project 2");
        expect(wrapper.text()).not.toContain("Not demo: Project 3");

    });

    it("sends an API request to make a new demo flight", async () => {
        mock.onPost(/api\/flights\/.+\/make_demo/).reply(200);
        await flushPromises();

        expect(mock.history.post).toHaveLength(0);
        let flightButton = wrapper.findAll("button")
            .filter(b => b.text() == "Not demo: Flight 2").at(0);
        await flightButton.trigger("click");
        await flushPromises();
        expect(mock.history.post).toHaveLength(1);
    });

    it("sends an API request to delete a demo flight", async () => {
        mock.onDelete(/api\/flights\/.+\/delete_demo/).reply(200);
        await flushPromises();

        expect(mock.history.delete).toHaveLength(0);
        let flightButton = wrapper.findAll("button")
            .filter(b => b.text() == "Demo: Flight 1").at(0);
        await flightButton.trigger("click");
        await flushPromises();
        expect(mock.history.delete).toHaveLength(1);
    });

    it("sends an API request to make a new demo project", async () => {
        mock.onPost(/api\/projects\/.+\/make_demo/).reply(200);
        await flushPromises();

        expect(mock.history.post).toHaveLength(0);
        let projectButton = wrapper.findAll("button")
            .filter(b => b.text() == "Not demo: Project 2").at(0);
        await projectButton.trigger("click");
        await flushPromises();
        expect(mock.history.post).toHaveLength(1);
    });

    it("sends an API request to delete a demo project", async () => {
        mock.onDelete(/api\/projects\/.+\/delete_demo/).reply(200);
        await flushPromises();

        expect(mock.history.delete).toHaveLength(0);
        let projectButton = wrapper.findAll("button")
            .filter(b => b.text() == "Demo: Project 1").at(0);
        await projectButton.trigger("click");
        await flushPromises();
        expect(mock.history.delete).toHaveLength(1);
    });
})