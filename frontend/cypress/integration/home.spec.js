/// <reference types="cypress" />

context('Home screen', () => {
  beforeEach(() => {
    cy.visit("/")
  })

  it("Shows a description of the app", () => {
    cy.contains("Procesamiento de imágenes de drones").should("be.visible");
    cy.contains("Mapas georreferenciados del terreno, en formatos PNG y GeoTIFF").should("be.visible");
    cy.contains("$65/mes").should("be.visible");
  })
})