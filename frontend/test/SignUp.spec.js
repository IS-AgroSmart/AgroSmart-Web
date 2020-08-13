import {
    createLocalVue,
    mount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import SignUp from 'components/SignUp.vue';

import BootstrapVue from 'bootstrap-vue';
import ReactiveStorage from "vue-reactive-localstorage";

const localVue = createLocalVue();
localVue.use(BootstrapVue);
localVue.use(ReactiveStorage, {
    "token": "",
    "isAdmin": false,
    "otherUserPk": 0,
    "loggedInUser": {}
});

import axios from 'axios'
import MockAdapter from 'axios-mock-adapter';

describe('Account creation component', () => {
    let wrapper, mock;

    beforeEach(() => {
        wrapper = mount(SignUp, {
            localVue
        });
        mock = new MockAdapter(axios);
    });

    afterEach(function () {
        mock.restore();
    });

    it("has the right title and two buttons", async () => {
        expect(wrapper.text()).toContain("Crear cuenta");
        expect(wrapper.findAll("button")).toHaveLength(2);
    });

    it("sets the vars to user inputs", async () => {
        let inputs = wrapper.findAll("input");
        expect(inputs).toHaveLength(5);
        await inputs.at(0).setValue("myusername");
        expect(wrapper.vm.form.username).toBe("myusername");
        await inputs.at(1).setValue("My Real Name");
        expect(wrapper.vm.form.first_name).toBe("My Real Name");
        await inputs.at(2).setValue("supersecret");
        expect(wrapper.vm.form.password).toBe("supersecret");
        await inputs.at(3).setValue("email@example.com");
        expect(wrapper.vm.form.email).toBe("email@example.com");
        await inputs.at(4).setValue("Organization");
        expect(wrapper.vm.form.organization).toBe("Organization");
    });

    it("sends API request with all data", async () => {
        mock.onPost("api/users/").reply(200);

        let inputs = wrapper.findAll("input");
        await inputs.at(0).setValue("myusername");
        await inputs.at(1).setValue("My Real Name");
        await inputs.at(2).setValue("supersecret");
        await inputs.at(3).setValue("email@example.com");
        await inputs.at(4).setValue("Organization");
        await wrapper.find("form").trigger("submit");
        await flushPromises();

        expect(mock.history.post).toHaveLength(1);
        let requestData = JSON.parse(mock.history.post[0].data);
        expect(requestData).toHaveProperty("username", "myusername");
        expect(requestData).toHaveProperty("email", "email@example.com");
        expect(requestData).toHaveProperty("first_name", "My Real Name");
    });

    it("shows error message when network error", async () => {
        mock.onPost("api/users/").networkError();

        await wrapper.find("form").trigger("submit");
        await flushPromises();

        expect(mock.history.post).toHaveLength(1);
        expect(wrapper.text()).toContain("Network Error");
    });

    it("shows error message when fields wrong", async () => {
        mock.onPost("api/users/").reply(400, {
            username: ["Not funny enough!", "Already taken"],
            password: ["Too short"]
        });

        await wrapper.find("form").trigger("submit");
        await flushPromises();

        expect(wrapper.text()).toContain("username: Not funny enough!");
        expect(wrapper.text()).toContain("username: Already taken");
        expect(wrapper.text()).toContain("password: Too short");
    });
});