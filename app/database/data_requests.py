from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert, and_
from .models import Invoice, Product, Statistic, Composition
from datetime import date

# Invoice
async def insert_invoice(session: AsyncSession, number: int, date: date, cost: float):
    stmt = insert(Invoice).values(number=number, date=date, delivery_cost=cost)
    await session.execute(stmt)
    await session.commit()

# Product
async def insert_product(session: AsyncSession, invoice_number: int, name: str, quantity: int, purchase_price: float):
    stmt = insert(Product).values(invoice_number=invoice_number, name=name, quantity=quantity, purchase_price=purchase_price)
    await session.execute(stmt)
    await session.commit()

async def get_product_names(session: AsyncSession, is_promotion: bool = False):
    if is_promotion:
        stmt = (select(Product.id, Product.name, Invoice.date, Statistic.remaining_pieces, Statistic.lost_pieces)
                .join(Invoice, Product.invoice_number == Invoice.number)
                .join(Statistic, Statistic.product_id == Product.id)
                .where(and_(Statistic.end.is_(False), Statistic.promotion_price != 0))
        )
    else:
        stmt = (select(Product.id, Product.name, Invoice.date, Statistic.remaining_pieces, Statistic.lost_pieces)
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
        "lost_pieces": row[4]
        }
        for row in result.fetchall()
    ]

async def get_product_id(session: AsyncSession, name: str, invoice_number: int):
    stmt = select(Product.id).where(Product.name == name, Product.invoice_number == invoice_number)
    result = await session.execute(stmt)

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
        data: tuple,
        product_ids: list[int]
):
    product_id, quantity = data
    if product_id not in product_ids:
        return False, ("Не вышло! Выберите данные из предложенного списка. "
                       "Попробуйте заново, или введите /cancel.")
    result = await get_product_remaining(session, product_id)
    if result is not None:
        remaining_pieces, = result
        print(remaining_pieces)
        if remaining_pieces >= quantity:
            sold_pieces, sale_price = await get_product_sold_pieces(session, product_id)
            sold_pieces += quantity
            total_standard_revenue = sold_pieces * sale_price
            remaining_pieces -= quantity
            end = True if remaining_pieces == 0 else False

            stat_stmt = (
                update(Statistic)
                .where(and_(Statistic.product_id == product_id, Statistic.end.is_(False)))
                .values(sold_pieces=sold_pieces,
                        total_standard_revenue=total_standard_revenue,
                        remaining_pieces=remaining_pieces,
                        end=end)
            )
            product_stmt = (
                update(Product)
                .where(Product.id == product_id)
                .values(end=end)
            )
            await session.execute(stat_stmt)
            await session.execute(product_stmt)
            await session.commit()

            return True, "Данные успешно внесены."
        else:
            return False, ("Не вышло! Вы хотите продать больше товара, чем есть, "
                           "попробуйте заново, или введите /cancel.")
    else:
        return False, ("Не вышло! Идентификатор товара не существует, "
                        "попробуйте заново, или нажмите /cancel.")

async def update_product_promotion_revenue(
        session: AsyncSession,
        data: tuple,
        product_ids: list[int]
):
    product_id, quantity = data
    if product_id not in product_ids:
        return False, ("Не вышло! Выберите данные из предложенного списка. "
                       "Попробуйте заново, или введите /cancel.")
    result = await get_product_remaining(session, product_id)
    if result is not None:
        remaining_pieces, = result
        if remaining_pieces >= quantity:
            promotion_pieces, promotion_price = await get_product_promotion_pieces(session, product_id)
            if promotion_price == 0:
                return False, ("Не вышло! Для этого товара не установлена акционная цена, "
                               "попробуйте заново, или нажмите /cancel.")
            else:
                promotion_pieces += quantity
                total_promotion_revenue = promotion_pieces * promotion_price
                remaining_pieces -= quantity
                end = True if remaining_pieces == 0 else False

                stat_stmt = (
                    update(Statistic)
                    .where(and_(Statistic.product_id == product_id, Statistic.end.is_(False)))
                    .values(promotion_pieces=promotion_pieces,
                            total_promotion_revenue=total_promotion_revenue,
                            remaining_pieces=remaining_pieces,
                            end=end)
                )
                product_stmt = (
                    update(Product)
                    .where(Product.id == product_id)
                    .values(end=end)
                )
                await session.execute(stat_stmt)
                await session.execute(product_stmt)
                await session.commit()

                return True, "Данные успешно внесены."
        else:
            return False, ("Не вышло! Вы хотите продать больше товара, чем есть, "
                           "попробуйте заново, или введите /cancel.")
    else:
        return False, ("Не вышло! Идентификатор товара не существует, "
                        "попробуйте заново, или нажмите /cancel.")

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

async def get_trash_data(session: AsyncSession, product_id: int):
    stmt = (
        select(Statistic.lost_pieces, Statistic.lost_money, Product.purchase_price)
        .join(Product, Product.id == Statistic.product_id)
        .where(and_(Statistic.product_id == product_id, Statistic.end.is_(False)))
    )
    result = await session.execute(stmt)

    row = result.fetchone()
    if row:
        return row
    else:
        # Не внесен приход
        return None


async def add_trash(
        session: AsyncSession,
        data: list[tuple],
        product_ids: list[int]
):
    for trash_data in data:
        product_id, _ = trash_data
        print(product_ids)
        if product_id not in product_ids:
            return False, ("Не вышло! Выберите данные из предложенного списка. "
                           "Попробуйте заново, или введите /cancel.")
    for trash_data in data:
        product_id, quantity = trash_data
        result = await get_product_remaining(session, product_id)
        if result is not None:
            remaining_pieces, = result
            if remaining_pieces >= quantity:
                lost_pieces, _, purchase_price = await get_trash_data(session, product_id)
                lost_pieces += quantity
                lost_money = lost_pieces * purchase_price
                remaining_pieces -= quantity
                end = True if remaining_pieces == 0 else False

                stat_stmt = (
                    update(Statistic)
                    .where(and_(Statistic.product_id == product_id, Statistic.end.is_(False)))
                    .values(lost_pieces=lost_pieces,
                            lost_money=lost_money,
                            remaining_pieces=remaining_pieces,
                            end=end)
                )
                product_stmt = (
                    update(Product)
                    .where(Product.id == product_id)
                    .values(end=end)
                )

                await session.execute(stat_stmt)
                await session.execute(product_stmt)
            else:
                return False, ("Не вышло! Вы хотите внести утиля больше чем есть товара, "
                            "попробуйте заново, или введите /cancel.")
        else:
            return False, ("Не вышло! Идентификатор товара не существует, "
                            "попробуйте заново, или нажмите /cancel.")
    await session.commit()

    return True, "Данные успешно внесены."

async def get_stat_prices(
        session: AsyncSession,
        product_id: int
):
    stmt = (
        select(Statistic.sale_price, Statistic.promotion_price)
        .where(and_(Statistic.product_id == product_id, Statistic.end.is_(False)))
    )
    result = await session.execute(stmt)

    row = result.fetchone()
    if row:
        return row
    else:
        # product_id не существует
        return None

async def change_price(
        session: AsyncSession,
        data: list[tuple],
        is_stnd_change_price: bool,
        product_ids: list[int]
):
    for changed_data in data:
        product_id, _ = changed_data
        if product_id not in product_ids:
            return False, ("Не вышло! Выберите данные из предложенного списка. "
                           "Попробуйте заново, или введите /cancel.")
    for changed_data in data:
        product_id, new_price = changed_data
        sale_price, promotion_price = await get_stat_prices(session, product_id)
        sold_pieces, _ = await get_product_sold_pieces(session, product_id)
        promotion_pieces, _ = await get_product_promotion_pieces(session, product_id)
        result = await get_product_remaining(session, product_id)
        if result is not None:
            if sold_pieces == 0 and promotion_pieces == 0:
                if is_stnd_change_price:
                    stmt = (
                        update(Statistic)
                        .where(and_(Statistic.product_id == product_id, Statistic.end.is_(False)))
                        .values(sale_price=new_price)
                    )
                else:
                    stmt = (
                        update(Statistic)
                        .where(and_(Statistic.product_id == product_id, Statistic.end.is_(False)))
                        .values(promotion_price=new_price)
                    )
                await session.execute(stmt)
            else:
                stat_stmt = (
                    update(Statistic)
                    .where(and_(Statistic.product_id == product_id, Statistic.end.is_(False)))
                    .values(remaining_pieces=0,
                            price_change=True,
                            end=True)
                )
                await session.execute(stat_stmt)

                remaining_pieces, = result
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
        else:
            return False, ("Не вышло! Идентификатор товара не существует, "
                            "попробуйте заново, или нажмите /cancel.")
    await session.commit()

    return True, "Данные успешно внесены."

# Composition
async def get_next_composition_id(session: AsyncSession) -> int:
    stmt = select(func.coalesce(func.max(Composition.composition_id), 0) + 1)
    result = await session.execute(stmt)
    return result.scalar()

async def insert_composition(
        session: AsyncSession,
        data: list[tuple],
        product_ids: list[int]
):
    composition_id = await get_next_composition_id(session)
    print(session.get_transaction())
    print(session.in_transaction())
    async with session.begin():
        # for sell_data in data:
        #     _, product_id, _, _ = sell_data
            # if product_id not in product_ids:
            #     return False, ("Не вышло! Выберите данные из предложенного списка. "
            #                 "Попробуйте заново, или введите /cancel.")
        for sell_data in data:
            is_trash, product_id, sold_pieces, sale_price = sell_data
            if product_id not in product_ids:
                return False, ("Не вышло! Выберите данные из предложенного списка. "
                            "Попробуйте заново, или введите /cancel.")
            if is_trash:
                lost_pieces, _, purchase_price = await get_trash_data(session, product_id)
                if lost_pieces >= sold_pieces:
                    total_revenue = sold_pieces * sale_price
                    lost_pieces -= sold_pieces
                    lost_money = lost_pieces * purchase_price

                    composition_stmt = insert(Composition).values(composition_id=composition_id,
                                                                    product_id=product_id,
                                                                    sold_pieces=sold_pieces,
                                                                    sale_price=sale_price,
                                                                    total_revenue=total_revenue)
                    stat_stmt = (
                        update(Statistic)
                        .where(and_(Statistic.product_id == product_id, Statistic.end.is_(False)))
                        .values(lost_pieces=lost_pieces,
                                lost_money=lost_money)
                    )
                    await session.execute(stat_stmt)
                    await session.execute(composition_stmt)
                else:
                    return False, ("Не вышло! Вы хотите продать больше утиля, чем есть, "
                                    "попробуйте заново, или введите /cancel.")
            else:
                result = await get_product_remaining(session, product_id)
                if result is not None:
                    remaining_pieces, = result
                    if remaining_pieces >= sold_pieces:
                        total_revenue = sold_pieces * sale_price
                        remaining_pieces -= sold_pieces
                        end = True if remaining_pieces == 0 else False
                        
                        composition_stmt = insert(Composition).values(composition_id=composition_id,
                                                                    product_id=product_id,
                                                                    sold_pieces=sold_pieces,
                                                                    sale_price=sale_price,
                                                                    total_revenue=total_revenue)
                        stat_stmt = (
                            update(Statistic)
                            .where(and_(Statistic.product_id == product_id, Statistic.end.is_(False)))
                            .values(remaining_pieces=remaining_pieces,
                                    end=end)
                        )
                        product_stmt = (
                            update(Product)
                            .where(Product.id == product_id)
                            .values(end=end)
                        )
                        await session.execute(stat_stmt)
                        await session.execute(product_stmt)
                        await session.execute(composition_stmt)
                    else:
                        return False, ("Не вышло! Вы хотите продать больше товара, чем есть, "
                                    "попробуйте заново, или введите /cancel.")
                else:
                    return False, ("Не вышло! Идентификатор товара не существует, "
                                "попробуйте заново, или нажмите /cancel.")

        # await session.commit()

    return True, "Данные успешно внесены."
    
