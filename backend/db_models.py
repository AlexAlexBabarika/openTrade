import enum

from sqlalchemy import Enum, PrimaryKeyConstraint, String
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column

class Base(MappedAsDataclass, DeclarativeBase):
    pass


class AssetType(str, enum.Enum):
    STOCK = 'stock'
    OPTION = 'option'
    CRYPTO = 'crypto'
    FOREX = 'forex'
    COMMODITY = 'commodity'
    INDEX = 'index'
    BOND = 'bond'
    ETF = 'etf'
    MUTUAL_FUND = 'mutual_fund'
    OTHER = 'other'


class Symbol(Base):
    __tablename__ = 'symbol'
    __table_args__ = (
        PrimaryKeyConstraint('symbol', name='symbol_pkey'),
    )

    symbol: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    exchange: Mapped[str] = mapped_column(String(50), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType, values_callable=lambda cls: [member.value for member in cls], name='asset_type'), nullable=False)
