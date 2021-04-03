import {
    createLocalVue,
    mount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import BlockCriteria from 'components/BlockCriteria.vue';

import {
    DropdownPlugin,
    CardPlugin,
    LayoutPlugin,
    AlertPlugin,
    FormInputPlugin,
    FormPlugin,
    FormGroupPlugin,
    ButtonPlugin,
    FormSelectPlugin,
} from 'bootstrap-vue';
import ReactiveStorage from "vue-reactive-localstorage";

const localVue = createLocalVue();
localVue.use(DropdownPlugin);
localVue.use(CardPlugin);
localVue.use(LayoutPlugin);
localVue.use(AlertPlugin);
localVue.use(FormInputPlugin);
localVue.use(FormPlugin);
localVue.use(FormGroupPlugin);
localVue.use(ButtonPlugin);
localVue.use(FormSelectPlugin);
localVue.prototype.$isLoggedIn = () => true;
localVue.use(ReactiveStorage, {
    "token": "newtoken",
    "isAdmin": false,
    "otherUserPk": 0,
    "loggedInUser": {}
});

import axios from 'axios'
import MockAdapter from 'axios-mock-adapter';

describe('Active Users component', () => {
    let wrapper, mock;

    function mountComponent() {
        wrapper = mount(BlockCriteria, {
            localVue,
            mocks: {
                $bvToast: {
                    toast: jest.fn(),
                },
                $router: {
                    push: jest.fn(),
                }
            },
        });
    }

    beforeEach(() => {
        mock = new MockAdapter(axios);
        mock.onGet("api/block_criteria/").replyOnce(200, [{
            pk: 1,
            type: "USER_NAME",
            value: "spammyusername",
            ip: ""
        }, {
            pk: 3,
            type: "USER_NAME",
            value: "anotherusername",
            ip: ""
        }, {
            pk: 4,
            type: "DOMAIN",
            value: "spam.com",
            ip: ""
        }, {
            pk: 5,
            type: "IP",
            value: "0.0.0.0",
            ip: ""
        }]);
    });

    afterEach(function () {
        mock.restore();
    });

    it("shows all criteria", async () => {
        mountComponent();
        await flushPromises();

        expect(wrapper.findAll(".card")).toHaveLength(4);
        expect(wrapper.text().includes("spammyusername")).toBe(true);
        expect(wrapper.text().includes("spam.com")).toBe(true);
        expect(wrapper.text().includes("anotherusername")).toBe(true);
        expect(wrapper.text().includes("0.0.0.0")).toBe(true);
        expect(mock.history.get).toHaveLength(1);
    });

    it("redirects to login if not logged in", async () => {
        localVue.prototype.$isLoggedIn = () => false;
        mountComponent();
        await flushPromises();

        expect(wrapper.vm.$router.push).toHaveBeenCalled();
    });

    it("can delete a block criterion", async () => {
        mountComponent();
        await flushPromises();

        mock.onDelete(/api\/block_criteria\/\d+\//).replyOnce(201, {});

        var firstCard = wrapper.find(".card");
        await firstCard.find("button").trigger("click");
        await flushPromises();
        expect(mock.history.delete).toHaveLength(1);
    });

    it("filters block criteria if a search string is set", async () => {
        mountComponent();
        await flushPromises();
        var input = wrapper.find("input[type=text]");
        expect(input.exists()).toBe(true);
        await input.setValue('spa');

        await wrapper.vm.$nextTick(); // Allow for recomputing 
        expect(wrapper.findAll(".card")).toHaveLength(2);
        expect(wrapper.text().includes("spammyusername")).toBe(true);
        expect(wrapper.text().includes("spam.com")).toBe(true);
        expect(wrapper.text().includes("anotherusername")).toBe(false);
        expect(wrapper.text().includes("0.0.0.0")).toBe(false);
    });

    it("shows an error message on connection error when deleting", async () => {
        mountComponent();
        await flushPromises();
        mock.onDelete(/api\/block_criteria\/\d+\//).networkError();

        var firstCard = wrapper.find(".card");
        await firstCard.find("button").trigger("click");
        await flushPromises();

        expect(wrapper.vm.$bvToast.toast).toHaveBeenCalled();
    });

    it("creates a new block criteria", async () => {
        mountComponent();
        await flushPromises();
        mock.onPost(/api\/block_criteria\//).reply(201, {});
        expect(mock.history.post).toHaveLength(0);

        var firstOption = wrapper.findAll("select>option").at(1);
        expect(firstOption.text()).toBe("IP");
        firstOption.element.selected = true
        await wrapper.find('select').trigger('change');
        await wrapper.vm.$nextTick();
        var ipInput = wrapper.find("#input-3");
        expect(ipInput.exists()).toBe(true);
        await ipInput.setValue('1.2.3.4');
        var submitButton = wrapper.find("button");
        expect(submitButton.text()).toBe("Crear");
        await submitButton.trigger("click");
        await flushPromises();

        expect(mock.history.post).toHaveLength(1);
        expect(JSON.parse(mock.history.post[0].data)).toHaveProperty("type", "IP");
        expect(JSON.parse(mock.history.post[0].data)).toHaveProperty("value", "");
        expect(JSON.parse(mock.history.post[0].data)).toHaveProperty("ip", "1.2.3.4");
        expect(mock.history.post[0].headers).toHaveProperty("Authorization", "Token newtoken");
    });

    it("shows error toast if block criteria creation fails", async () => {
        mountComponent();
        await flushPromises();
        mock.onPost(/api\/block_criteria\//).networkError();
        expect(mock.history.post).toHaveLength(0);

        var submitButton = wrapper.find("button");
        expect(submitButton.text()).toBe("Crear");
        await submitButton.trigger("click");
        await flushPromises();

        expect(mock.history.post).toHaveLength(1);
        expect(wrapper.vm.$bvToast.toast).toHaveBeenCalledWith('Error al procesar la solicitud. Intente más tarde', expect.anything());
    });
})