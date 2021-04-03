import {
    createLocalVue,
    mount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import CreateIndex from 'components/CreateIndex.vue';

import BootstrapVue from 'bootstrap-vue';
import ReactiveStorage from "vue-reactive-localstorage";
import VueDebounce from 'vue-debounce'

const localVue = createLocalVue();
localVue.use(BootstrapVue);
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
localVue.prototype.$processingStepsODM = {
    10: "En cola",
    20: "Procesando",
    30: "Fallido",
    40: "Terminado",
    50: "Cancelado"
}
localVue.prototype.$processingStepsDjango = {
    "WAITING": "En cola",
    "PROCESSING": "Procesando",
    "ERROR": "Fallido",
    "COMPLETE": "Terminado",
    "CANCELED": "Cancelado"
  }
localVue.use(ReactiveStorage, {
    "token": "usertoken",
    "isAdmin": false,
    "otherUserPk": 0,
    "loggedInUser": {}
});
const moment = require('moment');
require('moment/locale/es');
localVue.use(require('vue-moment'), {
    moment
});
localVue.use(VueDebounce);

import axios from 'axios'
import MockAdapter from 'axios-mock-adapter';


describe("Index creation component", () => {
    let wrapper, mock;

    const mountComponent = () => {
        wrapper = mount(CreateIndex, {
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
    });

    afterEach(function () {
        mock.restore();
        wrapper.vm.storage.otherUserPk = 0;
    });

    it("shows flight info", async () => {
        mountComponent();

        expect(wrapper.text()).toContain("(");
        expect(wrapper.text()).toContain("*");
        expect(wrapper.text()).toContain("NIR");
    });

    test("index text fields are initially empty", async () => {
        mountComponent();

        const inputs = wrapper.findAll("input");
        expect(inputs).toHaveLength(2);
        expect(inputs.at(0).text()).toBe("");
        expect(inputs.at(1).text()).toBe("");
    });

    test("clicking on a button fills the second text field", async () => {
        mountComponent();

        const index = wrapper.findAll("input").at(1);
        expect(index.text()).toBe("");
        expect(wrapper.vm.formula).toBe("");

        const buttonRed = wrapper.find("button.btn-danger");
        expect(buttonRed.text()).toBe("R");
        await buttonRed.trigger("click");
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.formula).toBe("red");
    });

    it("sends an API request to check the formula", async () => {
        mountComponent();

        expect(wrapper.vm.formula).toBe("");
        wrapper.vm.formula = "red+nir-somethingweird"

        expect(wrapper.vm.indexOK).toBe(false);
        expect(wrapper.vm.indexWrong).toBe(false);
        mock.onPost("/api/rastercalcs/check").reply(200, {});
        wrapper.vm.checkFormula(); // Manually trigger the debounced method
        await flushPromises();

        expect(wrapper.vm.indexWrong).toBe(false);
        expect(wrapper.vm.indexOK).toBe(true);
    });

    it("sends check API request as other user", async () => {
        mountComponent();
        wrapper.vm.storage.otherUserPk = {
            pk: 123
        };

        mock.onPost("/api/rastercalcs/check").reply(200, {});
        wrapper.vm.checkFormula();
        await flushPromises();

        expect(mock.history.post[0].headers).toHaveProperty("TARGETUSER", 123);
    });

    it("reports if the formula was wrong", async () => {
        mountComponent();

        expect(wrapper.vm.formula).toBe("");

        expect(wrapper.vm.indexOK).toBe(false);
        expect(wrapper.text()).not.toContain("Error en la fórmula");

        mock.onPost("/api/rastercalcs/check").reply(400, {});
        wrapper.vm.checkFormula(); // Manually trigger the debounced method
        await flushPromises();

        expect(wrapper.vm.indexWrong).toBe(true);
        expect(wrapper.vm.indexOK).toBe(false);
        expect(wrapper.text()).toContain("Error en la fórmula");
    });

    it("sends the final API request when submit triggered", async () => {
        mountComponent();

        wrapper.vm.formula = "something";
        wrapper.vm.name = "clevername";
        mock.onPost("/api/rastercalcs/myuuid").reply(200, {});
        await wrapper.find('form').trigger('submit');
        await flushPromises();

        expect(mock.history.post).toHaveLength(1);
        expect(mock.history.post[0].headers).toHaveProperty("Authorization", "Token usertoken");
        expect(JSON.parse(mock.history.post[0].data)).toMatchObject({
            "formula": "something",
            "index": "clevername"
        });
    });

    it("sends final API request as other user", async () => {
        mountComponent();
        wrapper.vm.storage.otherUserPk = {
            pk: 123
        };

        wrapper.vm.formula = "something";
        wrapper.vm.name = "clevername";
        mock.onPost("/api/rastercalcs/myuuid").reply(200, {});
        await wrapper.find('form').trigger('submit');
        await flushPromises();

        expect(mock.history.post[0].headers).toHaveProperty("TARGETUSER", 123);
    });

    it("shows an error message when upload API returns error", async () => {
        mountComponent();

        mock.onPost("/api/rastercalcs/myuuid").networkError();
        await wrapper.find('form').trigger('submit');
        await flushPromises();

        expect(mock.history.post).toHaveLength(1);
        expect(wrapper.text()).toContain("Operación fallida");
    });

    it("shows error message when user is over quota", async () => {
        mountComponent();

        mock.onPost("/api/rastercalcs/myuuid").reply(402); // HTTP 402 Payment Required
        await wrapper.find("form").trigger("submit");
        await flushPromises();

        expect(wrapper.find('.alert-danger').exists()).toBe(true);
        expect(wrapper.text()).toContain("Operación fallida");
        expect(wrapper.text()).toContain("Su almacenamiento está lleno.");
    });
})