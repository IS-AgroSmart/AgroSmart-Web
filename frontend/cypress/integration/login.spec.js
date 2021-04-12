/// <reference types="cypress" />

context('Login', () => {
  beforeEach(() => {
    cy.visit('/')
  })

  it('Getting the title', () => {
    cy.title().should('eq', 'AgroSmart')
  })

  it("Attempting to log in with a wrong password", () => {
    cy.intercept({
      method: "POST",
      url: "/api/api-auth"
    }, {statusCode: 403})
    cy.intercept("GET", "/api/users", {statusCode: 403})

    cy.get("input[type='text']").type("nope")
    cy.get("input[type='password']").type("hello")
    cy.contains("button", "Iniciar sesión").click()
    cy.url().should('not.include', '/flights')
    cy.contains("div.alert-danger", "Usuario o contraseña incorrectos")
  })

  it("Logging in", () => {
    cy.intercept({
      method: "POST",
      url: "/api/api-auth"
    }, {
      token: "FOOBAR_token"
    })
    cy.intercept("GET", "/api/users", { fixture: 'users.json' }).as("getUsers")
    cy.intercept("GET", "/api/flights", { fixture: 'flights.json' }).as("getFlights")

    cy.get("input[type='text']").type("admin")
    cy.get("input[type='password']").type("admin")
    cy.contains("button", "Iniciar sesión").click()

    cy.wait("@getUsers").its("request.headers").should("have.a.property", "authorization", "Token FOOBAR_token")
    cy.url().should('include', '/flights')

  })
})