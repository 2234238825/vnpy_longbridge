from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_session
from .models import Asset, Fund, FundMember, Member, Position
from .models.accounting import TransactionType
from .schemas import AssetCreate, CashFlowCreate, FundCreate, MemberCreate, PriceUpdate, TradeCreate
from .services import FundService


router = APIRouter(prefix="/api")


def service(session: Session = Depends(get_session)) -> FundService:
    return FundService(session)


def commit(session: Session) -> None:
    session.commit()


@router.post("/funds", status_code=201)
def create_fund(payload: FundCreate, session: Session = Depends(get_session)) -> dict:
    fund = Fund(name=payload.name, initial_nav=payload.initial_nav)
    session.add(fund)
    session.commit()
    return {"id": fund.id, "name": fund.name, "initial_nav": fund.initial_nav}


@router.post("/members", status_code=201)
def create_member(payload: MemberCreate, session: Session = Depends(get_session)) -> dict:
    member = Member(name=payload.name, username=payload.username, role=payload.role)
    session.add(member)
    session.commit()
    return {"id": member.id, "name": member.name, "role": member.role}


@router.post("/assets", status_code=201)
def create_asset(payload: AssetCreate, session: Session = Depends(get_session)) -> dict:
    asset = Asset(**payload.model_dump())
    session.add(asset)
    session.commit()
    return {"id": asset.id, "symbol": asset.symbol}


@router.post("/funds/{fund_id}/subscriptions", status_code=201)
def subscribe(fund_id: int, payload: CashFlowCreate, session: Session = Depends(get_session)) -> dict:
    try:
        tx = FundService(session).subscribe(fund_id, payload.member_id, payload.amount, payload.currency)
        session.commit()
        return {"transaction_id": tx.id, "type": tx.type, "amount": tx.amount, "note": tx.note}
    except ValueError as exc:
        session.rollback()
        raise HTTPException(422, str(exc)) from exc


@router.post("/funds/{fund_id}/withdrawals", status_code=201)
def withdraw(fund_id: int, payload: CashFlowCreate, session: Session = Depends(get_session)) -> dict:
    try:
        tx = FundService(session).withdraw(fund_id, payload.member_id, payload.amount, payload.currency)
        session.commit()
        return {"transaction_id": tx.id, "type": tx.type, "amount": tx.amount, "note": tx.note}
    except ValueError as exc:
        session.rollback()
        raise HTTPException(422, str(exc)) from exc


@router.post("/funds/{fund_id}/trades", status_code=201)
def trade(fund_id: int, payload: TradeCreate, session: Session = Depends(get_session)) -> dict:
    try:
        side = TransactionType(payload.side.upper())
        tx = FundService(session).trade(fund_id, payload.asset_id, side, payload.quantity,
                                        payload.price, payload.fee, payload.currency)
        session.commit()
        return {"transaction_id": tx.id, "type": tx.type, "amount": tx.amount}
    except ValueError as exc:
        session.rollback()
        raise HTTPException(422, str(exc)) from exc


@router.put("/funds/{fund_id}/assets/{asset_id}/market-price")
def update_market_price(fund_id: int, asset_id: int, payload: PriceUpdate,
                        session: Session = Depends(get_session)) -> dict:
    try:
        position = FundService(session).update_market_price(fund_id, asset_id, payload.market_price)
        session.commit()
        return {"position_id": position.id, "market_value": position.market_value}
    except ValueError as exc:
        session.rollback()
        raise HTTPException(422, str(exc)) from exc


@router.post("/funds/{fund_id}/nav-snapshots", status_code=201)
def snapshot_nav(fund_id: int, session: Session = Depends(get_session)) -> dict:
    try:
        nav = FundService(session).snapshot_nav(fund_id, date.today())
        session.commit()
        return {"date": nav.date, "nav": nav.nav, "net_asset": nav.net_asset, "shares": nav.shares}
    except ValueError as exc:
        session.rollback()
        raise HTTPException(422, str(exc)) from exc


@router.get("/funds/{fund_id}/dashboard")
def dashboard(fund_id: int, session: Session = Depends(get_session)) -> dict:
    try:
        service = FundService(session)
        fund = service._fund(fund_id)
        members = session.execute(select(FundMember, Member).join(Member, FundMember.member_id == Member.id)
                                  .where(FundMember.fund_id == fund_id)).all()
        return {
            "fund": {"id": fund.id, "name": fund.name, "nav": service.current_nav(fund_id),
                     "net_asset": service.net_asset(fund_id), "shares": service.total_shares(fund_id)},
            "members": [
                {"name": member.name, "shares": ownership.shares,
                 "current_value": ownership.shares * service.current_nav(fund_id),
                 "total_deposit": ownership.total_deposit, "total_withdraw": ownership.total_withdraw}
                for ownership, member in members
            ],
        }
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/funds/{fund_id}/positions")
def positions(fund_id: int, session: Session = Depends(get_session)) -> list[dict]:
    rows = session.execute(select(Position, Asset).join(Asset, Position.asset_id == Asset.id)
                           .where(Position.fund_id == fund_id)).all()
    return [{"symbol": asset.symbol, "name": asset.name, "quantity": position.quantity,
             "cost": position.cost, "market_price": position.market_price,
             "market_value": position.market_value} for position, asset in rows]

