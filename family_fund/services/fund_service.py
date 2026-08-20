from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Asset, AuditLog, Fund, FundMember, FundNav, Member, Position, Transaction
from ..models.accounting import TransactionType


ZERO = Decimal("0")
CASH_SYMBOL = "CASH"


class FundService:
    """基金份额和持仓账务服务。所有金额参数必须是 Decimal。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def _fund(self, fund_id: int) -> Fund:
        fund = self.session.get(Fund, fund_id)
        if not fund:
            raise ValueError("基金不存在")
        return fund

    def _member(self, member_id: int) -> Member:
        member = self.session.get(Member, member_id)
        if not member:
            raise ValueError("成员不存在")
        return member

    def _fund_member(self, fund_id: int, member_id: int) -> FundMember:
        item = self.session.scalar(select(FundMember).where(
            FundMember.fund_id == fund_id, FundMember.member_id == member_id,
        ))
        if not item:
            self._member(member_id)
            item = FundMember(fund_id=fund_id, member_id=member_id)
            self.session.add(item)
            self.session.flush()
        return item

    def _cash_asset(self, currency: str) -> Asset:
        asset = self.session.scalar(select(Asset).where(
            Asset.symbol == CASH_SYMBOL, Asset.exchange == "", Asset.currency == currency,
        ))
        if not asset:
            asset = Asset(symbol=CASH_SYMBOL, name=f"{currency} 现金", asset_type="CASH", currency=currency)
            self.session.add(asset)
            self.session.flush()
        return asset

    def _position(self, fund_id: int, asset_id: int) -> Position:
        position = self.session.scalar(select(Position).where(
            Position.fund_id == fund_id, Position.asset_id == asset_id,
        ))
        if not position:
            position = Position(fund_id=fund_id, asset_id=asset_id)
            self.session.add(position)
            self.session.flush()
        return position

    def _audit(self, action: str, object_type: str, object_id: int, value: str, user_id: int | None = None) -> None:
        self.session.add(AuditLog(
            user_id=user_id, action=action, object_type=object_type,
            object_id=str(object_id), new_value=value,
        ))

    def total_shares(self, fund_id: int) -> Decimal:
        return self.session.scalar(select(func.coalesce(func.sum(FundMember.shares), ZERO)).where(
            FundMember.fund_id == fund_id,
        )) or ZERO

    def net_asset(self, fund_id: int) -> Decimal:
        return self.session.scalar(select(func.coalesce(func.sum(Position.market_value), ZERO)).where(
            Position.fund_id == fund_id,
        )) or ZERO

    def current_nav(self, fund_id: int) -> Decimal:
        fund = self._fund(fund_id)
        shares = self.total_shares(fund_id)
        return fund.initial_nav if shares == ZERO else self.net_asset(fund_id) / shares

    def subscribe(self, fund_id: int, member_id: int, amount: Decimal, currency: str = "USD") -> Transaction:
        if amount <= ZERO:
            raise ValueError("申购金额必须大于 0")
        self._fund(fund_id)
        nav = self.current_nav(fund_id)
        shares = amount / nav
        ownership = self._fund_member(fund_id, member_id)
        ownership.shares += shares
        ownership.total_deposit += amount
        cash = self._position(fund_id, self._cash_asset(currency).id)
        cash.quantity += amount
        cash.market_price = Decimal("1")
        cash.cost += amount
        cash.market_value += amount
        transaction = Transaction(
            fund_id=fund_id, member_id=member_id, asset_id=cash.asset_id,
            type=TransactionType.DEPOSIT.value, amount=amount, currency=currency,
            note=f"按净值 {nav} 申购 {shares} 份",
        )
        self.session.add(transaction)
        self.session.flush()
        self._audit("SUBSCRIBE", "transaction", transaction.id, transaction.note, member_id)
        return transaction

    def withdraw(self, fund_id: int, member_id: int, amount: Decimal, currency: str = "USD") -> Transaction:
        if amount <= ZERO:
            raise ValueError("赎回金额必须大于 0")
        nav = self.current_nav(fund_id)
        shares = amount / nav
        ownership = self._fund_member(fund_id, member_id)
        if ownership.shares < shares:
            raise ValueError("可赎回份额不足")
        cash = self._position(fund_id, self._cash_asset(currency).id)
        if cash.market_value < amount:
            raise ValueError("基金可用现金不足")
        ownership.shares -= shares
        ownership.total_withdraw += amount
        cash.quantity -= amount
        cash.cost -= amount
        cash.market_value -= amount
        transaction = Transaction(
            fund_id=fund_id, member_id=member_id, asset_id=cash.asset_id,
            type=TransactionType.WITHDRAW.value, amount=amount, currency=currency,
            note=f"按净值 {nav} 赎回 {shares} 份",
        )
        self.session.add(transaction)
        self.session.flush()
        self._audit("WITHDRAW", "transaction", transaction.id, transaction.note, member_id)
        return transaction

    def trade(self, fund_id: int, asset_id: int, side: TransactionType, quantity: Decimal,
              price: Decimal, fee: Decimal = ZERO, currency: str = "USD") -> Transaction:
        if side not in (TransactionType.BUY, TransactionType.SELL):
            raise ValueError("交易方向只支持 BUY 或 SELL")
        if quantity <= ZERO or price <= ZERO or fee < ZERO:
            raise ValueError("数量和价格必须大于 0，手续费不能为负")
        self._fund(fund_id)
        asset = self.session.get(Asset, asset_id)
        if not asset:
            raise ValueError("资产不存在")
        amount = quantity * price
        position = self._position(fund_id, asset_id)
        cash = self._position(fund_id, self._cash_asset(currency).id)
        if side is TransactionType.BUY:
            if cash.market_value < amount + fee:
                raise ValueError("可用现金不足")
            old_cost = position.cost
            position.quantity += quantity
            position.cost += amount + fee
            position.avg_price = position.cost / position.quantity
            position.market_price = price
            position.market_value = position.quantity * price
            cash.quantity -= amount + fee
            cash.cost -= amount + fee
            cash.market_value -= amount + fee
        else:
            if position.quantity < quantity:
                raise ValueError("持仓数量不足")
            cost_released = position.cost * quantity / position.quantity
            position.quantity -= quantity
            position.cost -= cost_released
            position.avg_price = ZERO if position.quantity == ZERO else position.cost / position.quantity
            position.market_price = price
            position.market_value = position.quantity * price
            cash.quantity += amount - fee
            cash.cost += amount - fee
            cash.market_value += amount - fee
        transaction = Transaction(
            fund_id=fund_id, asset_id=asset_id, type=side.value, quantity=quantity,
            price=price, amount=amount, fee=fee, currency=currency,
        )
        self.session.add(transaction)
        self.session.flush()
        self._audit(side.value, "transaction", transaction.id, f"{asset.symbol} {quantity} @ {price}")
        return transaction

    def update_market_price(self, fund_id: int, asset_id: int, market_price: Decimal) -> Position:
        if market_price < ZERO:
            raise ValueError("市价不能为负")
        position = self._position(fund_id, asset_id)
        position.market_price = market_price
        position.market_value = position.quantity * market_price
        self._audit("MARK_TO_MARKET", "position", position.id, f"price={market_price}")
        return position

    def snapshot_nav(self, fund_id: int, snapshot_date: date | None = None) -> FundNav:
        snapshot_date = snapshot_date or date.today()
        total_asset = self.net_asset(fund_id)
        shares = self.total_shares(fund_id)
        nav = self.current_nav(fund_id)
        previous = self.session.scalar(select(FundNav).where(
            FundNav.fund_id == fund_id, FundNav.date < snapshot_date,
        ).order_by(FundNav.date.desc()))
        daily_return = ZERO if not previous or previous.nav == ZERO else nav / previous.nav - Decimal("1")
        record = self.session.scalar(select(FundNav).where(
            FundNav.fund_id == fund_id, FundNav.date == snapshot_date,
        ))
        if not record:
            record = FundNav(fund_id=fund_id, date=snapshot_date, total_asset=total_asset,
                             net_asset=total_asset, shares=shares, nav=nav, daily_return=daily_return)
            self.session.add(record)
        else:
            record.total_asset, record.net_asset = total_asset, total_asset
            record.shares, record.nav, record.daily_return = shares, nav, daily_return
        self.session.flush()
        self._audit("SNAPSHOT_NAV", "fund_nav", record.id, f"nav={nav}")
        return record

