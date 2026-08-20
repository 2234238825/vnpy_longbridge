from decimal import Decimal

from pydantic import BaseModel, Field


class FundCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    initial_nav: Decimal = Decimal("1")


class MemberCreate(BaseModel):
    name: str
    username: str
    role: str = "MEMBER"


class CashFlowCreate(BaseModel):
    member_id: int
    amount: Decimal = Field(gt=0)
    currency: str = "USD"


class AssetCreate(BaseModel):
    symbol: str
    name: str
    asset_type: str
    currency: str = "USD"
    exchange: str = ""


class TradeCreate(BaseModel):
    asset_id: int
    side: str
    quantity: Decimal = Field(gt=0)
    price: Decimal = Field(gt=0)
    fee: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = "USD"


class PriceUpdate(BaseModel):
    market_price: Decimal = Field(ge=0)

