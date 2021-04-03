import {
    createLocalVue,
    mount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import FlightReport from 'components/FlightReport.vue';

import {
    ButtonPlugin,
    CardPlugin,
    AlertPlugin,
    FormPlugin,
    FormGroupPlugin,
    FormCheckboxPlugin,
    LayoutPlugin,
} from 'bootstrap-vue'
import ReactiveStorage from "vue-reactive-localstorage";

const localVue = createLocalVue();
localVue.use(ButtonPlugin);
localVue.use(CardPlugin);
localVue.use(AlertPlugin);
localVue.use(FormPlugin);
localVue.use(FormCheckboxPlugin);
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
import {
    layerGroup
} from 'leaflet';

describe("Project list component", () => {
    let wrapper, mock;
    window.URL.createObjectURL = jest.fn();

    const mountComponent = () => {
        wrapper = mount(FlightReport, {
            localVue,
            mocks: {
                $route: {
                    params: {
                        uuid: "myuuid"
                    }
                }
            },
        });
    };

    beforeEach(() => {
        mock = new MockAdapter(axios);
        mock.onGet(/api\/flights\/.+/).reply(200, {
            uuid: "flightuuid",
            name: "Flight Name"
        })
    });

    afterEach(function () {
        mock.restore();
        wrapper.vm.storage.otherUserPk = 0;
        window.URL.createObjectURL.mockReset();
    });

    it("calls API and fills flight info", async () => {
        mountComponent();
        await flushPromises();

        expect(wrapper.text()).toContain("Flight Name");
        // 1st is /api/users, 2nd is /api/flights/uuid
        expect(mock.history.get).toHaveLength(2);
    });

    it("calls API as other user", async () => {
        wrapper.vm.storage.otherUserPk = {
            pk: 123
        };
        mountComponent();
        await flushPromises();

        // 1st is /api/users, 2nd is /api/flights/uuid
        expect(mock.history.get[1].headers).toHaveProperty("TARGETUSER", 123);
    });

    it("shows the available sections", async () => {
        mountComponent();
        await flushPromises();

        expect(wrapper.text()).toContain("Ortomosaico");
        expect(wrapper.text()).toContain("Datos generales");
    });

    it("disallows download when nothing selected", async () => {
        mountComponent();
        await flushPromises();
        expect(wrapper.findAll("button[disabled]")).toHaveLength(0);

        wrapper.vm.selected = [];
        await wrapper.vm.$nextTick();
        expect(wrapper.findAll("button[disabled]")).toHaveLength(1);
    });

    it("sends an API request to download report", async () => {
        mountComponent();
        await flushPromises();
        // 1st is /api/users, 2nd is /api/flights/uuid
        expect(mock.history.get).toHaveLength(2);
        mock.onGet(/api\/downloads\/.+\/report.pdf/).reply(200);

        await wrapper.findAll("input[type=checkbox]").at(1).trigger("click"); // Toggle orthomosaic
        await wrapper.find('form').trigger('submit');
        await flushPromises();

        expect(mock.history.get).toHaveLength(3);
        expect(mock.history.get[2].url).toContain("api/downloads/flightuuid/report.pdf");
        expect(mock.history.get[2].params).toHaveProperty("generaldata");
        expect(mock.history.get[2].params).not.toHaveProperty("orthomosaic");
    });

    it("shows an error message when endpoint returns error", async () => {
        mountComponent();
        await flushPromises();
        // 1st is /api/users, 2nd is /api/flights/uuid
        expect(mock.history.get).toHaveLength(2);
        mock.onGet(/api\/downloads\/.+\/report.pdf/).reply(400, "awesome error description");

        let alert = wrapper.find("div.alert");
        expect(alert.exists()).toBe(false);
        await wrapper.find('form').trigger('submit');
        await flushPromises();

        alert = wrapper.find("div.alert");
        expect(alert.exists()).toBe(true);
        expect(alert.text()).toContain("400");
    });
})