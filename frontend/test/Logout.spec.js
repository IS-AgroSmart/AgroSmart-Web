import {
    createLocalVue,
    mount
} from '@vue/test-utils';
import flushPromises from "flush-promises";

import Logout from 'components/Logout.vue';

import ReactiveStorage from "vue-reactive-localstorage";

const localVue = createLocalVue();
localVue.use(ReactiveStorage, {
    "token": "mytoken",
    "isAdmin": false,
    "otherUserPk": 0,
    "loggedInUser": {
        pk: 123,
        first_name: "My Real Name",
        email: "user@server.com"
    }
});

import axios from 'axios'
import MockAdapter from 'axios-mock-adapter';

describe('Logout component', () => {
    let wrapper, mock;

    beforeEach(() => {
        wrapper = mount(Logout, {
            localVue,
            mocks: {
                $router: {
                    replace: jest.fn(),
                },
            },
        });
        mock = new MockAdapter(axios);
    });

    afterEach(function () {
        mock.restore();
    });

    it("unsets token and user dict", async () => {
        await flushPromises();

        expect(wrapper.vm.storage.token).toBe("");
        expect(wrapper.vm.storage.loggedInUser).toStrictEqual({});
    });

    it("navigates to homepage", async () => {
        await flushPromises();
        expect(wrapper.vm.$router.replace).toHaveBeenCalledWith("/");
    });
});