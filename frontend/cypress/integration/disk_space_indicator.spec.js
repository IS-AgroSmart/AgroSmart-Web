/// <reference types="cypress" />

context('Disk space indicator', () => {
  beforeEach(() => {
    
  })

  it("Displays the disk bar for a normal user", () => {
    cy.visit("/")
    cy.login("admin")

    cy.get(".progress").parent().should("contain.text", "20.00 GB de 45.00 GB usados")
    cy.get(".progress").find("div[role='progressbar']").should("have.attr", "aria-valuenow", 20)
  })

  it("Displays the full disk bar for a full-disk user", () => {
    cy.visit("/")
    cy.login("bob")

    cy.get(".progress").parent().should("contain.text", "45.00 GB de 45.00 GB usados")
    cy.get(".progress").find("div[role='progressbar']").should("have.attr", "aria-valuenow", 45)
  })
})