/// <reference types="cypress" />

context('Flight list', () => {
  beforeEach(() => {
    cy.visit("/")
    cy.login("admin")
  })

  it("Lists all flights", () => {
    cy.intercept("GET", "/api/flights", {
      fixture: 'flights.json'
    }).as("getFlights")
    cy.get("[data-cy='navbar-flights']").click();

    cy.wait("@getFlights")
    cy.get("[data-cy='flight-card']").should('have.length.at.least', 2)
  })

  it('Show details of Flight', function () {
    cy.intercept("GET", "/api/flights/*", {
      fixture: 'single_flight.json'
    })

    cy.intercept("/nodeodm/task/*/info", {
      "imagesCount": 1234,
      "processingTime": 60000
    })
    cy.intercept("/nodeodm/task/*/output", [])
    cy.intercept("/api/preview/*", '{"url": "nope"}')
    cy.intercept("/api/downloads/*/thumbnail", {
      fixture: "images/thumbnail.png"
    })

    cy.get("[data-cy='navbar-flights']").click();
    cy.contains("[data-cy='flight-card']", "First Flight").find(".btn").click();

    cy.contains("Resultados")
    cy.contains("Estado: Terminado")
  });
})