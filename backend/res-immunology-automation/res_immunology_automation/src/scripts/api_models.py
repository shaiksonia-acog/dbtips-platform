from pydantic import BaseModel, Field, constr
from typing import List, Optional, Dict, Literal


class TargetRequest(BaseModel):
    target: str
    diseases: List[str] = Field(default_factory=list)

class TargetOnlyRequest(BaseModel):
    target: constr(min_length=1)  # Requires at least one character

class GraphRequest(BaseModel):
    target_gene: str
    target_diseases: list[str]
    metapath: Literal["GGGD", "DGPG"]

class DiseaseRequest(BaseModel):
    disease: str  # Ensure disease is a string

class DiseasesRequest(BaseModel):
    diseases: List[str]

class ExcelExportRequest(BaseModel):
    endpoint: str
    target: Optional[str] = None  # Make 'target' optional
    diseases: Optional[List[str]] = None  # Make 'diseases' optional

class Pagination(BaseModel):
    index: int = Field(0, description="Page index, default is 0")
    size: int = Field(3, description="Number of records per page, default is 3")

class SearchQueryModel(BaseModel):
    queryString: str = Field(..., description="The search query string")
    entityNames: Optional[List[str]] = Field(default=["disease"], description="List of entity names, default is ["
                                                                              "'disease']")
    page: Optional[Pagination] = Field(default=Pagination(), description="Pagination settings with default index 0 "
                                                                         "and size 3")

class DiseaseRequestOnto(BaseModel):
    disease: str  # Ensure disease is a string
    search_page: str

class SearchRequest(BaseModel):
    searchText: str

# model will be used for blackbox warning on the market intelligence dashboard. specifically the approved drugs table
class DiseaseDrugsMapping(BaseModel):
    disease: str
    approved_drugs: List[str]

class DiseasesTarget(BaseModel):
    disease: List[str] | str = "no-disease"
    target: str = "no-target"

class LiteratureAnalysisRequest(BaseModel):
    targets: List[str] = Field(default_factory=lambda: ["no-target"])
    diseases: List[str] = Field(default_factory=lambda: ["no-disease"])

