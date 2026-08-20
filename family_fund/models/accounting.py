from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


MONEY = Numeric(20, 6)
QUANTITY = Numeric(20, 8)


class Role(StrEnum):
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"


class TransactionType(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"
    DIVIDEND = "DIVIDEND"
    INTEREST = "INTEREST"
    FEE = "FEE"
    TRANSFER = "TRANSFER"
    REVERSAL = "REVERSAL"


class Fund(Base):
    __tablename__ = "fund"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    initial_nav: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("1"))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class Member(Base):
    __tablename__ = "member"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), default="")
    role: Mapped[str] = mapped_column(String(20), default=Role.MEMBER.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class FundMember(Base):
    __tablename__ = "fund_member"
    __table_args__ = (UniqueConstraint("fund_id", "member_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    fund_id: Mapped[int] = mapped_column(ForeignKey("fund.id"))
    member_id: Mapped[int] = mapped_column(ForeignKey("member.id"))
    shares: Mapped[Decimal] = mapped_column(QUANTITY, default=Decimal("0"))
    total_deposit: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    total_withdraw: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class Asset(Base):
    __tablename__ = "asset"
    __table_args__ = (UniqueConstraint("symbol", "exchange", "currency"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(120))
    asset_type: Mapped[str] = mapped_column(String(20))
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    exchange: Mapped[str] = mapped_column(String(30), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class Position(Base):
    __tablename__ = "position"
    __table_args__ = (UniqueConstraint("fund_id", "asset_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    fund_id: Mapped[int] = mapped_column(ForeignKey("fund.id"))
    asset_id: Mapped[int] = mapped_column(ForeignKey("asset.id"))
    quantity: Mapped[Decimal] = mapped_column(QUANTITY, default=Decimal("0"))
    avg_price: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    cost: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    market_price: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    market_value: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class Transaction(Base):
    __tablename__ = "transaction"
    id: Mapped[int] = mapped_column(primary_key=True)
    fund_id: Mapped[int] = mapped_column(ForeignKey("fund.id"))
    member_id: Mapped[int | None] = mapped_column(ForeignKey("member.id"), nullable=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("asset.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[Decimal] = mapped_column(QUANTITY, default=Decimal("0"))
    price: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    amount: Mapped[Decimal] = mapped_column(MONEY)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    fee: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    trade_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    note: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class FundNav(Base):
    __tablename__ = "fund_nav"
    __table_args__ = (UniqueConstraint("fund_id", "date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    fund_id: Mapped[int] = mapped_column(ForeignKey("fund.id"))
    date: Mapped[date] = mapped_column(Date)
    total_asset: Mapped[Decimal] = mapped_column(MONEY)
    total_liability: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    net_asset: Mapped[Decimal] = mapped_column(MONEY)
    shares: Mapped[Decimal] = mapped_column(QUANTITY)
    nav: Mapped[Decimal] = mapped_column(MONEY)
    daily_return: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("member.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    object_type: Mapped[str] = mapped_column(String(100))
    object_id: Mapped[str] = mapped_column(String(100))
    old_value: Mapped[str] = mapped_column(String, default="")
    new_value: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

