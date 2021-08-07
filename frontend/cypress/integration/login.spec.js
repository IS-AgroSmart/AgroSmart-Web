/// <reference types="cypress" />

context('Login', () => {
  beforeEach(() => {
    
  })

  it("Attempting to log in with a wrong password", () => {
    cy.intercept({
      method: "POST",
      url: "/api/api-auth"
    }, {statusCode: 403})
    cy.intercept("GET", "/api/users", {statusCode: 403})

    cy.visit('/#/login')
    cy.get("[data-cy='username']").type("nope")
    cy.get("[data-cy='password']").type("hello")
    cy.get("[data-cy='login']").click()

    cy.url().should('not.include', '/flights')
    cy.contains("[data-cy=alert]", "Usuario o contraseña incorrectos")
  })

  it("Successful login", () => {
    cy.intercept({
      method: "POST",
      url: "/api/api-auth"
    }, {
      token: "FOOBAR_token"
    })
    cy.intercept("GET", "/api/users", { fixture: 'users.json' }).as("getUsers")
    cy.intercept("GET", "/api/flights", { fixture: 'flights.json' }).as("getFlights")

    cy.visit('/')
    cy.get("[data-cy='navbar-login']").click()
    cy.get("[data-cy='username']").type("admin")
    cy.get("[data-cy='password']").type("admin")
    cy.get("[data-cy='login']").click()

    cy.wait("@getUsers").its("request.headers").should("have.a.property", "authorization", "Token FOOBAR_token")
    cy.contains("Mi cuenta").should("be.visible")
  })
})