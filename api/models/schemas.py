from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class ParametersBase(BaseModel):
    time: int = Field(..., description="Intervalle de rafraîchissement en secondes")
    nameFirstColumn: str = Field(..., description="Nom de la première colonne")
    nameSecondColumn: str = Field(..., description="Nom de la deuxième colonne")
    nameThirdColumn: str = Field(..., description="Nom de la troisième colonne")
    successColor: str = Field(..., description="Couleur pour les builds réussis")
    failureColor: str = Field(..., description="Couleur pour les builds échoués")

class ParametersCreate(ParametersBase):
    pass

class ParametersUpdate(ParametersBase):
    pass

class Parameters(ParametersBase):
    id: int = Field(..., description="ID unique des paramètres")

    class Config:
        from_attributes = True

class BuildAttributes(BaseModel):
    id: str = Field(..., description="ID du build")
    name: str = Field(..., description="Nom du build")
    projectName: str = Field(..., description="Nom du projet")
    webUrl: str = Field(..., description="URL du build")
    status: str = Field(..., description="Statut du build")
    state: str = Field(..., description="État du build")

class Build(BaseModel):
    attributes: BuildAttributes = Field(..., alias="@attributes")

    class Config:
        populate_by_name = True

class BuildResponse(BaseModel):
    id: str
    name: str
    projectName: str
    webUrl: str
    status: str
    state: str

class Project(BaseModel):
    name: str
    builds: List[BuildResponse]

class Category(BaseModel):
    name: str
    projects: List[Project]

class BuildsResponse(BaseModel):
    categories: Dict[str, Category] 