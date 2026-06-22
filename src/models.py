from pydantic import BaseModel, Field

class TicketData(BaseModel):
    client: str = Field(alias="Client")
    commande: str = Field(alias="Commande")
    date_livraison: str = Field(alias="DateLivraison")
    libelle: str = Field(alias="Libelle")
    gtin: str = Field(alias="CodeBarre01")
    date_expiration: str = Field(alias="CodeBarre17")  # Format YYMMDD
    lot: str = Field(alias="CodeBarre10")
    num_lot_display: str = Field(alias="Numlot")
    quantite: int = Field(alias="Quantite")

    class Config:
        populate_by_name = True
