from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession, AsyncConnection
from sqlalchemy import select, update, insert, and_
from .models import Invoice, Product, Statistic, Composition, MigrationStatus, OtherExpense
from datetime import date, datetime
from typing import Union
from collections import defaultdict

# ==============================================================================================================
# МИГРАЦИЯ ДАННЫХ
# ==============================================================================================================

async def is_migrations_ready(conn: AsyncConnection):
    result = await conn.execute(
        select(MigrationStatus)
        .where(MigrationStatus.status == "completed")
    )
    migration_status = result.scalar_one_or_none()
    return migration_status is not None

async def mark_migrations_is_ready(conn: AsyncConnection):
    await conn.execute(
        insert(MigrationStatus)
        .values(status="completed", date=datetime.now())
    )
    await conn.commit()

async def migrate_data(old_conn: AsyncConnection, new_conn: AsyncConnection):
    """
    Migrate data from a table in the old database to the new database.
    """
    old_result = await old_conn.execute(
        select(Statistic, Product, Invoice)
        .join(Product, Statistic.product_id == Product.id)
        .join(Invoice, Product.invoice_number == Invoice.number)
        .where(Statistic.end.is_(False))
    )
    statistics = old_result.all()

    product_inserts = []
    statistic_inserts = []
    for stat in statistics:
        (stat_id,
         stat_product_id,
         sold_pieces,
         sale_price,
         total_standard_revenue,
         lost_pieces,
         lost_money,
         remaining_pieces,
         promotion_pieces,
         promotion_price,
         total_promotion_revenue,
         price_change,
         stat_end,
         product_id,
         product_invoice_number,
         name,
         quantity,
         purchase_price,
         product_end,
         invoice_number,
         date,
         delivery_cost) = stat

        existing_invoice = await new_conn.execute(
            select(Invoice)
            .where(
                Invoice.number == invoice_number,
                Invoice.invoice_date == date
            )
        )
        existing_invoice = existing_invoice.scalar_one_or_none()
        # Insert Invoice
        if existing_invoice is None:
            await new_conn.execute(
                insert(Invoice)
                .values(
                    number=invoice_number,
                    invoice_date=date,
                    delivery_cost=delivery_cost
                )
            )
            new_conn.commit()

        # Insert Product
        product_inserts.append({
            'id': product_id,
            'invoice_number': invoice_number,
            'name': name,
            'quantity': quantity,
            'purchase_price': purchase_price,
            'end': product_end
        })

        # Insert Statistic
        statistic_inserts.append({
            'id': stat_id,
            'product_id': stat_product_id,
            'sold_pieces': sold_pieces,
            'sale_price': sale_price,
            'total_standard_revenue': total_standard_revenue,
            'lost_pieces': lost_pieces,
            'lost_money': lost_money,
            'remaining_pieces': remaining_pieces,
            'promotion_pieces': promotion_pieces,
            'promotion_price': promotion_price,
            'total_promotion_revenue': total_promotion_revenue,
            'price_change': price_change,
            'end': stat_end
        })

    if product_inserts:
        await new_conn.execute(insert(Product), product_inserts)
    if statistic_inserts:
        await new_conn.execute(insert(Statistic), statistic_inserts)

    await new_conn.commit()

    return True

# ==============================================================================================================
# ВНЕСЕНИЕ ПРИХОДА
# ==============================================================================================================

async def insert_invoice(session: AsyncSession, invoice_number: int, date: date, cost: float):
    existing_invoice = await session.execute(
        select(Invoice)
        .where(Invoice.number == invoice_number, Invoice.invoice_date == date)
    )
    if existing_invoice.scalar() is None:
        await session.execute(
            insert(Invoice)
            .values(number=invoice_number, invoice_date=date, delivery_cost=cost)
        )
        await session.commit()

# ==============================================================================================================
# ВЫВОД НАКЛАДНОЙ
# ==============================================================================================================

async def get_invoices(session: AsyncSession):
    result = await session.execute(
        select(
            Invoice.number,
            Invoice.invoice_date
        )
    )
    invoices = defaultdict(list)
    for number, date in result.fetchall():
        invoices[number].append(date)
    return invoices

async def get_products_by_invoice(
        session: Union[AsyncSession, AsyncConnection],
        invoice_number: int,
        date: date
):
    result = await session.execute(
        select(
            Product.name,
            Product.quantity,
            Product.purchase_price
        )
        .where(
            Product.invoice_number == invoice_number,
            Invoice.invoice_date == date
        )
        .join(
            Invoice,
            Invoice.number == invoice_number
        )
    )
    return result.fetchall()


# ==============================================================================================================
# ДЛЯ ДРУГИХ ТРАТ
# ==============================================================================================================

async def get_expenses_data(
        session: AsyncSession
):
    result = await session.execute(select(OtherExpense))
    return result.scalars().all()

async def get_expence_spent(
      session: AsyncSession,
      expence_id: int  
):
    result = await session.execute(
        select(OtherExpense.spent)
        .where(OtherExpense.id == expence_id)
    )

    return result.scalar()

async def add_other_expense(
        session: AsyncSession,
        expense_id: int,
        expense_name: int,
        additional_spent: int
):
    # добавляем к существующей трате
    if expense_name is None:
        spent = await get_expence_spent(session, expense_id)
        spent += additional_spent

        result = await session.execute(
            update(OtherExpense)
            .where(OtherExpense.id == expense_id)
            .values(
                spent=spent
            )
            .returning(OtherExpense.name)
        )
        expense_name = result.scalar()
    # Создаем новую трату
    else:
        result = await session.execute(
            insert(OtherExpense)
            .values(
                name=expense_name,
                spent=additional_spent,
            )
            .returning(OtherExpense.id)
        )
        expense_id = result.scalar()
        spent = additional_spent

    await session.commit()
    return expense_id, expense_name, spent

# Product
async def insert_product(session: AsyncSession, invoice_number: int, name: str, quantity: int, purchase_price: float):
    result = await session.execute(
        insert(Product)
        .values(
            invoice_number=invoice_number,
            name=name,
            quantity=quantity,
            purchase_price=purchase_price
        )
        .returning(Product.id)
    )
    await session.commit()

    return result.scalar()

async def get_product_names(session: AsyncSession, is_promotion: bool = False):
    if is_promotion:
        stmt = (
            select(
                Product.id,
                Product.name,
                Invoice.invoice_date,
                Statistic.remaining_pieces,
                Statistic.lost_pieces,
                Statistic.sale_price,
                Statistic.promotion_price
            )
                .join(Invoice, Product.invoice_number == Invoice.number)
                .join(Statistic, Statistic.product_id == Product.id)
                .where(and_(Statistic.end.is_(False), Statistic.promotion_price != 0))
        )
    else:
        stmt = (
            select(
                Product.id,
                Product.name,
                Invoice.invoice_date,
                Statistic.remaining_pieces,
                Statistic.lost_pieces,
                Statistic.sale_price,
                Statistic.promotion_price
            )
                .join(Invoice, Product.invoice_number == Invoice.number)
                .join(Statistic, Statistic.product_id == Product.id)
                .where(Statistic.end.is_(False))
        )
    result = await session.execute(stmt)

    return [
        {
        "id":row[0],
        "name":row[1].lower(),
        "date":row[2],
        "remaining_pieces":row[3],
        "lost_pieces": row[4],
        "sale_price": row[5],
        "promotion_price": row[6]
        }
        for row in result.fetchall()
    ]

async def get_product_name(session: AsyncSession, product_id: int):
    result = await session.execute(
        select(Product.name)
        .where(
            Product.id == product_id
        )
    )
    return result.scalar_one_or_none()

async def get_product_remaining(session: AsyncSession, product_id: int):
    stmt = (
        select(Statistic.remaining_pieces)
        .where(and_(Statistic.product_id == product_id, Statistic.end.is_(False)))
    )
    result = await session.execute(stmt)

    row = result.fetchone()
    if row:
        return row
    else:
        return None

async def get_product_sold_pieces(session: AsyncSession, product_id: int):
    stmt = (
        select(Statistic.sold_pieces, Statistic.sale_price)
        .where(and_(Statistic.product_id == product_id, Statistic.end.is_(False)))
    )
    result = await session.execute(stmt)

    return result.fetchone()

async def get_product_promotion_pieces(session: AsyncSession, product_id: int):
    stmt = (
        select(Statistic.promotion_pieces, Statistic.promotion_price)
        .where(and_(Statistic.product_id == product_id, Statistic.end.is_(False)))
    )
    result = await session.execute(stmt)

    return result.fetchone()

async def update_product_revenue(
        session: AsyncSession,
        product_id: int,
        remaining_pieces: int,
        quantity: int

):
    sold_pieces, sale_price = await get_product_sold_pieces(session, product_id)
    sold_pieces += quantity
    total_standard_revenue = sold_pieces * sale_price
    remaining_pieces -= quantity
    end = True if remaining_pieces == 0 else False

    result = await session.execute(
        update(Statistic)
        .where(and_(Statistic.product_id == product_id, Statistic.end.is_(False)))
        .values(sold_pieces=sold_pieces,
                total_standard_revenue=total_standard_revenue,
                remaining_pieces=remaining_pieces,
                end=end)
        .returning(Statistic.remaining_pieces)
    )
    await session.execute(
        update(Product)
        .where(Product.id == product_id)
        .values(end=end)
    )
    await session.commit()

    return result.scalar()

async def update_product_promotion_revenue(
        session: AsyncSession,
        product_id: int,
        remaining_pieces: int,
        quantity: int
):
    promotion_pieces, promotion_price = await get_product_promotion_pieces(session, product_id)
    promotion_pieces += quantity
    total_promotion_revenue = promotion_pieces * promotion_price
    remaining_pieces -= quantity
    end = True if remaining_pieces == 0 else False

    result = await session.execute(
        update(Statistic)
        .where(and_(Statistic.product_id == product_id, Statistic.end.is_(False)))
        .values(promotion_pieces=promotion_pieces,
                total_promotion_revenue=total_promotion_revenue,
                remaining_pieces=remaining_pieces,
                end=end)
        .returning(Statistic.remaining_pieces)
    )
    await session.execute(
        update(Product)
        .where(Product.id == product_id)
        .values(end=end)
    )
    await session.commit()

    return result.scalar()

# Statistic
async def start_statistics(
        session: AsyncSession,
        product_id: int,
        sale_price: float,
        quantity: int,
        promotion_price: float
):
    stmt = insert(Statistic).values(product_id=product_id,
                                    sale_price=sale_price,
                                    remaining_pieces=quantity,
                                    promotion_price=promotion_price)
    await session.execute(stmt)
    await session.commit()

# Добавление утиля
async def get_trash_data(session: AsyncSession, product_id: int):
    result = await session.execute(
        select(Product.purchase_price)
        .join(Statistic, Statistic.product_id == Product.id)
        .where(and_(Statistic.product_id == product_id, Statistic.end.is_(False)))
    )

    return result.scalar()

async def add_trash(
        session: AsyncSession,
        product_id: int,
        lost_pieces: int,
        quantity: int,
        remaining_pieces: int
):
    purchase_price = await get_trash_data(session, product_id)
    lost_pieces += quantity
    lost_money = lost_pieces * purchase_price
    end = True if remaining_pieces == 0 else False

    result = await session.execute(
        update(Statistic)
        .where(and_(Statistic.product_id == product_id, Statistic.end.is_(False)))
        .values(lost_pieces=lost_pieces,
                lost_money=lost_money,
                remaining_pieces=remaining_pieces,
                end=end)
        .returning(Statistic.lost_pieces)
    )
    await session.execute(
        update(Product)
        .where(Product.id == product_id)
        .values(end=end)
    )
    await session.commit()

    return result.scalar()

# Изменение цены
async def change_price(
        session: AsyncSession,
        product_id: int,
        remaining_pieces: int,
        is_stnd_change_price: bool,
        new_price: float
):
    sold_pieces, sale_price = await get_product_sold_pieces(session, product_id)
    promotion_pieces, promotion_price = await get_product_promotion_pieces(session, product_id)
    if sold_pieces == 0 and promotion_pieces == 0:
        if is_stnd_change_price:
            await session.execute(
                update(Statistic)
                .where(and_(Statistic.product_id == product_id, Statistic.end.is_(False)))
                .values(sale_price=new_price)
            )
        else:
            await session.execute(
                update(Statistic)
                .where(and_(Statistic.product_id == product_id, Statistic.end.is_(False)))
                .values(promotion_price=new_price)
            )
    else:
        await session.execute(
            update(Statistic)
            .where(and_(Statistic.product_id == product_id, Statistic.end.is_(False)))
            .values(remaining_pieces=0,
                    price_change=True,
                    end=True)
        )
        if is_stnd_change_price:
            await start_statistics(
                session=session,
                product_id=product_id,
                sale_price=new_price,
                quantity=remaining_pieces,
                promotion_price=promotion_price
            )
        else:
            await start_statistics(
                session=session,
                product_id=product_id,
                sale_price=sale_price,
                quantity=remaining_pieces,
                promotion_price=new_price
            )
    await session.commit()

# Добавление композиции
# async def get_next_composition_id(session: AsyncSession) -> int:
#     stmt = select(func.coalesce(func.max(Composition.composition_id), 0) + 1)
#     result = await session.execute(stmt)
#     return result.scalar()

async def insert_composition(
        session: AsyncSession,
        product_id: int,
        quantity: int,
        sale_price: float,
        remaining_pieces: int
):
    total_revenue = quantity * sale_price
    end = True if remaining_pieces == 0 else False
    
    await session.execute(
        insert(Composition)
        .values(
            product_id=product_id,
            sold_pieces=quantity,
            sale_price=sale_price,
            total_revenue=total_revenue
        )
    )
    await session.execute(
        update(Statistic)
        .where(and_(Statistic.product_id == product_id, Statistic.end.is_(False)))
        .values(
            remaining_pieces=remaining_pieces,
            end=end)
    )
    await session.execute(
        update(Product)
        .where(Product.id == product_id)
        .values(end=end)
    )
    await session.commit()

# ==============================================================================================================
# ДЛЯ ОТЧЕТОВ
# ==============================================================================================================

async def get_total_revenues(session: AsyncSession):
    subquery_statistics = select(
        func.sum(Statistic.total_standard_revenue).label("total_standard"),
        func.sum(Statistic.total_promotion_revenue).label("total_promotion")
    ).subquery()

    subquery_composition = select(
        func.sum(Composition.total_revenue).label("total_composition")
    ).subquery()

    result = await session.execute(
        select(
            subquery_statistics.c.total_standard,
            subquery_statistics.c.total_promotion,
            subquery_composition.c.total_composition
        )
    )
    totals = result.first()
    return {
        "total_standard_revenue": totals.total_standard or 0,
        "total_promotion_revenue": totals.total_promotion or 0,
        "total_composition_revenue": totals.total_composition or 0,
    }

async def get_purchase_expenses(session: AsyncSession):
    subquery_lost_money = select(
        func.sum(Statistic.lost_money).label("total_lost")
    ).subquery()
    subquery_purchase = select(
        func.sum(Product.quantity * Product.purchase_price).label("total_purchase")
    ).subquery()
    result = await session.execute(
        select(
            subquery_lost_money.c.total_lost,
            subquery_purchase.c.total_purchase
        )
    )
    totals = result.first()
    return {
        "total_lost": totals.total_lost or 0,
        "total_purchase": totals.total_purchase or 0,
    }