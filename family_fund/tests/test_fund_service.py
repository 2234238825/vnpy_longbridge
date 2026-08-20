from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from family_fund.db import Base
from family_fund.models import Asset, Fund, Member
from family_fund.models.accounting import TransactionType
from family_fund.services import FundService


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db


def setup_fund(session: Session) -> tuple[Fund, Member, Member]:
    fund = Fund(name="家庭基金", initial_nav=Decimal("1"))
    dad = Member(name="爸爸", username="dad")
    mom = Member(name="妈妈", username="mom")
    session.add_all([fund, dad, mom])
    session.commit()
    return fund, dad, mom


def test_subscription_uses_current_nav_without_diluting_existing_member(session: Session) -> None:
    fund, dad, mom = setup_fund(session)
    service = FundService(session)
    service.subscribe(fund.id, dad.id, Decimal("100000"))
    session.commit()

    cash = service._position(fund.id, service._cash_asset("USD").id)
    cash.market_value = Decimal("120000")
    service.subscribe(fund.id, mom.id, Decimal("60000"))
    session.commit()

    dad_holding = service._fund_member(fund.id, dad.id)
    mom_holding = service._fund_member(fund.id, mom.id)
    assert dad_holding.shares == Decimal("100000")
    assert mom_holding.shares == Decimal("50000")
    assert service.current_nav(fund.id) == Decimal("1.2")


def test_trade_updates_cash_and_position_then_nav_uses_market_value(session: Session) -> None:
    fund, dad, _ = setup_fund(session)
    service = FundService(session)
    service.subscribe(fund.id, dad.id, Decimal("10000"))
    asset = Asset(symbol="MSFT", name="Microsoft", asset_type="STOCK", currency="USD")
    session.add(asset)
    session.flush()
    service.trade(fund.id, asset.id, TransactionType.BUY, Decimal("10"), Decimal("500"))
    service.update_market_price(fund.id, asset.id, Decimal("600"))
    session.commit()

    assert service.net_asset(fund.id) == Decimal("11000")
    assert service.current_nav(fund.id) == Decimal("1.1")


def test_withdrawal_reduces_shares_at_current_nav(session: Session) -> None:
    fund, dad, _ = setup_fund(session)
    service = FundService(session)
    service.subscribe(fund.id, dad.id, Decimal("1000"))
    cash = service._position(fund.id, service._cash_asset("USD").id)
    cash.market_value = Decimal("1200")
    cash.quantity = Decimal("1200")
    service.withdraw(fund.id, dad.id, Decimal("120"))
    session.commit()

    holding = service._fund_member(fund.id, dad.id)
    assert holding.shares == Decimal("900")
    assert service.current_nav(fund.id) == Decimal("1.2")
