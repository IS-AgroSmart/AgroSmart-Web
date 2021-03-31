import {
    createLocalVue,
    mount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import NewProject from 'components/NewProject.vue';

import BootstrapVue from 'bootstrap-vue';
import ReactiveStorage from "vue-reactive-localstorage";
import Multiselect from 'vue-multiselect';

const localVue = createLocalVue();
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
localVue.use(BootstrapVue);
localVue.component('multiselect', Multiselect);
localVue.use(ReactiveStorage, {
    "token": "mytoken",
    "isAdmin": false,
    "otherUserPk": 0,
    "loggedInUser": {}
});

import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';

describe('New Project component', () => {
    let wrapper, mock;

    function mountComponent() {
        wrapper = mount(NewProject, {
            localVue,
            mocks: {
                $router: {
                    push: jest.fn(),
                },
            },
        });
    }

    beforeEach(() => {
        mock = new MockAdapter(axios);
        mock.onGet("api/flights").reply(200, [{
            uuid: "uuid1",
            name: "First Flight",
            camera: "RGB",
            state: "COMPLETE",
            is_demo: false
        }, {
            uuid: "uuid2",
            name: "Second Flight",
            camera: "RGB",
            state: "COMPLETE",
            is_demo: false
        }, {
            uuid: "uuid3",
            name: "Third Flight",
            camera: "REDEDGE",
            state: "COMPLETE",
            is_demo: false
        }, {
            uuid: "uuid4",
            name: "Fourth Flight",
            camera: "RGB",
            state: "PROCESSING",
            is_demo: false
        }, {
            uuid: "uuid5",
            name: "Demo Flight",
            camera: "RGB",
            state: "COMPLETE",
            is_demo: true
        }
        ]);
    });

    afterEach(function () {
        mock.restore();
        wrapper.vm.storage.otherUserPk = 0;
    });

    it("posts correctly if all successful", async () => {
        mountComponent();
        mock.onPost("api/projects/").reply(200, {});

        wrapper.find('form').trigger('submit');
        await flushPromises();

        expect(mock.history.post).toHaveLength(1);
        expect(mock.history.post[0].headers).toHaveProperty("Authorization", "Token mytoken");
        expect(wrapper.find('.alert-danger').exists()).toBeFalsy();
        expect(wrapper.vm.$router.push).toHaveBeenCalledWith("/projects");
    });

    it("posts as other user", async () => {
        wrapper.vm.storage.otherUserPk = {
            pk: 123
        };
        mountComponent();
        mock.onPost("api/projects/").reply(200, {});

        wrapper.find('form').trigger('submit');
        await flushPromises();

        expect(mock.history.post).toHaveLength(1);
        expect(mock.history.post[0].headers).toHaveProperty("TARGETUSER", 123);
    });

    it("shows error message", async () => {
        mountComponent();
        mock.onPost("api/projects/").reply(400, {
            name: ["too boring"]
        });

        wrapper.find('form').trigger('submit');
        await flushPromises();

        expect(mock.history.post).toHaveLength(1);

        let alert = wrapper.find('.alert-danger')
        expect(alert.exists()).toBe(true);
        expect(alert.text()).toBe("ERROR: too boring");
    });

    it("renders the correct flight names", async () => {
        mountComponent();
        await flushPromises();

        expect(mock.history.get).toHaveLength(1);

        expect(wrapper.text()).toContain("First Flight (RGB)");
        expect(wrapper.text()).toContain("Second Flight (RGB)");
        expect(wrapper.text()).toContain("Third Flight (Micasense Rededge)");
        expect(wrapper.text()).not.toContain("Fourth Flight");
    });

    it("doesnt't show Demo flights", async () => {
        mountComponent();
        await flushPromises();

        expect(wrapper.text()).not.toContain("Demo Flight");
    });

    it("requests flights as other user", async () => {
        wrapper.vm.storage.otherUserPk = {
            pk: 123
        };
        mountComponent();
        await flushPromises();

        expect(mock.history.get[0].headers).toHaveProperty("TARGETUSER", 123);
    });

    it("sets form flights when some flights clicked", async () => {
        mountComponent();
        await flushPromises();

        expect(wrapper.vm.form.flights).toHaveLength(0);
        wrapper.vm.form.flights = [wrapper.vm.flights[0]];
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.form.flights).toHaveLength(1);
    });

    it("indicates if all selected flights are from same camera", async () => {
        mountComponent();
        await flushPromises();

        wrapper.vm.form.flights = [wrapper.vm.flights[0]];
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.sameCamera).toBe(true);

        wrapper.vm.form.flights = [wrapper.vm.flights[0], wrapper.vm.flights[1]];
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.sameCamera).toBe(true);

        wrapper.vm.form.flights = [wrapper.vm.flights[2]];
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.sameCamera).toBe(true);

        wrapper.vm.form.flights = [wrapper.vm.flights[0], wrapper.vm.flights[2]];
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.sameCamera).toBe(false);
    });

    it("bumps to login page if not logged in already", async () => {
        localVue.prototype.$isLoggedIn = () => false;
        mountComponent();
        wrapper.find('form').trigger('submit');
        await flushPromises();

        expect(wrapper.vm.$router.push).toHaveBeenCalledWith("/login");
    });
});