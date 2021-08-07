// eslint-disable-next-line no-unused-vars
Cypress.Commands.add('login', (userType, options = {}) => {
  const types = {
    admin: {
      username: "admin",
      password: "admin",
    },
    user: {
      username: 'alice',
      password: "nope",
    },
    bob: {
      username: "bob_fulldisk",
      password: "bob"
    }
  }

  cy.intercept({
    method: "POST",
    url: "/api/api-auth"
  }, {
    token: "FOOBAR_token"
  })
  cy.intercept("GET", "/api/users", {
    fixture: 'users.json'
  })
  cy.intercept("GET", "/api/flights", {
    fixture: 'flights.json'
  })

  const user = types[userType]

  cy.visit("/#/login")
  cy.get("[data-cy='username']").type(user.username)
  cy.get("[data-cy='password']").type(user.password)
  cy.get("[data-cy='login']").click()
})