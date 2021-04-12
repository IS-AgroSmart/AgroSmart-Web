/// <reference types="cypress" />

context('Flight list', () => {
  beforeEach(() => {
    cy.visit("/")
    cy.login("admin")
  })

  it("Lists all flights", () => {
    cy.get("div.card").should('have.length.at.least', 2)
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

    cy.contains(".card", "First Flight").find(".btn").click();

    cy.contains("Resultados")
    cy.contains("Estado: Terminado")
  });
})