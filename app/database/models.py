from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine

from sqlalchemy import Integer, Boolean, ForeignKey, Text, Date, DateTime, Float
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint

from datetime import datetime, date

class UserBase(AsyncAttrs, DeclarativeBase):
    pass

class DataBase(AsyncAttrs, DeclarativeBase):
    pass

class User(UserBase):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    tg_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)

class MigrationStatus(DataBase):
    __tablename__ = 'migration_status'

    status: Mapped[str] = mapped_column(Text, primary_key=True)
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

class Invoice(DataBase):
    __tablename__ = "invoices"

    number: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, primary_key=True, nullable=False)
    delivery_cost: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")

    products: Mapped[list["Product"]] = relationship("Product", back_populates="invoice")

    __table_args__ = (UniqueConstraint("number", "invoice_date", name="uix_number_date"),)

class Product(DataBase):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    invoice_number: Mapped[int] = mapped_column(Integer, ForeignKey("invoices.number"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    purchase_price: Mapped[float] = mapped_column(Float, nullable=False)
    end: Mapped[bool] = mapped_column(Boolean, server_default="0")

    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="products")
    statistics: Mapped[list["Statistic"]] = relationship("Statistic", back_populates="product", foreign_keys="Statistic.product_id")
    composition: Mapped[list["Composition"]] = relationship("Composition", back_populates="product")

class Statistic(DataBase):
    __tablename__ = "statistics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    sold_pieces: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    sale_price: Mapped[float] = mapped_column(Float, nullable=False)
    total_standard_revenue: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    lost_pieces: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    lost_money: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    remaining_pieces: Mapped[int] = mapped_column(Integer, nullable=False)
    promotion_pieces: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    promotion_price: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    total_promotion_revenue: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    price_change: Mapped[bool] = mapped_column(Boolean, server_default="0")
    end: Mapped[bool] = mapped_column(Boolean, ForeignKey("products.end"), server_default="0")

    product: Mapped["Product"] = relationship("Product", back_populates="statistics", foreign_keys=[product_id])

class Composition(DataBase):
    __tablename__ = "compositions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    sold_pieces: Mapped[int] = mapped_column(Integer, nullable=False)
    sale_price: Mapped[float] = mapped_column(Float, nullable=False)
    total_revenue: Mapped[float] = mapped_column(Float, nullable=False)

    product: Mapped["Product"] = relationship("Product", back_populates="composition")

class OtherExpense(DataBase):
    __tablename__ = "other_expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    spent: Mapped[float] = mapped_column(Float)