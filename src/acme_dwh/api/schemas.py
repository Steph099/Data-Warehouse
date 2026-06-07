"""Pydantic response DTOs. Asset/DataSource use snake_case keys; the time-series
response uses camelCase (assetId, businessDate, ...) — both per the project doc."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from acme_dwh.dal.models import Asset, DataSource, TimeSeriesRecord, Value


class AssetDetail(BaseModel):
    id: str
    system_time: datetime
    name: str | None = None
    description: str | None = None
    attributes: dict[str, str] = {}
    deleted: bool = False

    @classmethod
    def from_model(cls, a: Asset) -> "AssetDetail":
        return cls(id=a.id, system_time=a.system_time, name=a.name,
                   description=a.description, attributes=a.attributes, deleted=a.deleted)


class DataSourceDetail(BaseModel):
    id: str
    system_time: datetime
    name: str | None = None
    description: str | None = None
    attributes: list[str] = []
    deleted: bool = False

    @classmethod
    def from_model(cls, s: DataSource) -> "DataSourceDetail":
        return cls(id=s.id, system_time=s.system_time, name=s.name,
                   description=s.description, attributes=sorted(s.attributes), deleted=s.deleted)


class DataRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    business_date: date = Field(alias="businessDate")
    values: dict[str, Value]

    @classmethod
    def from_model(cls, r: TimeSeriesRecord) -> "DataRecord":
        return cls(business_date=r.business_date, values=r.values)


class DataPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    asset_id: str = Field(alias="assetId")
    data_source_id: str = Field(alias="dataSourceId")
    records: list[DataRecord]


class DataResponse(BaseModel):
    data: DataPayload
    attributes: list[str] | None = None  # populated only when includeAttributes=true


# ---- Ingestion ----
class IngestRequest(BaseModel):
    symbols: list[str]
    provider: str | None = None
    start: date | None = None
    end: date | None = None


class IngestStatsModel(BaseModel):
    symbol: str
    assetId: str
    dataSourceId: str
    fetched: int
    transformed: int
    stored: int
    skipped: int
    failed: int
    attributes: list[str]


# ---- Analytics ----
class TotalRow(BaseModel):
    year: int
    count: int
    minClose: float | None = None
    maxClose: float | None = None
    avgClose: float | None = None


class PredictionRow(BaseModel):
    businessDate: date
    open: float | None = None
    prediction: float | None = None


class JobRunRequest(BaseModel):
    assetId: str | None = None
    dataSourceId: str | None = None


class JobRunResult(BaseModel):
    ok: bool
    job: str
    assetId: str | None = None
    dataSourceId: str | None = None
    rowsWritten: int | None = None
    durationSeconds: float
    message: str
    logTail: str


# ---- Assistant ----
class AssistantRequest(BaseModel):
    question: str


class AssistantStep(BaseModel):
    tool: str
    args: dict
    ok: bool


class AssistantResponse(BaseModel):
    answer: str | None = None
    steps: list[AssistantStep] = []
    error: str | None = None
