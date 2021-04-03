import axios from "axios";

/**
 * Queries the /api/users endpoint and filters the users(s) returned by username
 * @param {string} token An API token for a user
 * @param {string} username The username of the user that will be returned
 * @returns A tuple (user, error). If error is not null, user is null, and viceversa.
 */
async function getUserInfo(token, username) {
    try {
        let response = await axios.get("api/users", { headers: { "Authorization": "Token " + token } });
        return [response.data.find((u) => u.username == username), null];
    } catch (e) {
        return [null, e];
    }
}

export {
    getUserInfo
}