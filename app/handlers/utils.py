import re
import asyncio
from datetime import datetime
from rapidfuzz import process
from rapidfuzz import fuzz

# Я сделал стоимость доставки обязаельным, поэтому надо подредактировать функцию
async def process_invoice_data(raw_data: str):
    header_regex = r"^(\d+)/(\d{2}\.\d{2}\.\d{2})(?:/(\d+(?:\.\d+)?))?$" # Matches "3961/15.07.24" or "3961/15.07.24/200.45"
    product_regex = r"^([^/]+)/(\d+)/(\d+(\.\d+)?)/(\d+(\.\d+)?)(?:/(\d+(?:\.\d+)?))?$" # Matches "Хризантема/20/50/100/70"

    lines = raw_data.strip().split("\n")
    lines = [line.strip() for line in lines if line.strip()]

    if not lines or len(lines) < 2:
        return False, "Неверный формат ввода данных. Слишком мало строк."

    header_match = re.match(header_regex, lines[0])
    if not header_match:
        return False, ("ОШИБКА: Неверный формат для номера, даты накладной или стоимости доставки.\n"
                       "Пожалуйста, введите данные в формате: [Номер накладной]/[Дата] "
                       "или [Номер накладной]/[Дата]/[Стоимость доставки].")
    invoice_number, date, cost = header_match.groups()
    try:
        invoice_number = int(invoice_number)
        date = datetime.strptime(date, "%d.%m.%y").date()
        cost = float(cost) if cost else 0.
    except ValueError:
        return False, (f"ОШИБКА: Неверный формат поля [Номер накладной], [Дата] или [Стоимость доставки].\n\n"
                       "Правила:\n"
                       "1. В поле [Номер накладной] должно быть натуральное число, т.е. 50 или 1.\n"
                       "2. В поле [Дата] должно быть строка в формате дд.мм.гг, т.е. 20.10.24.\n"
                       "3. В опциональном поле [Стоимость доставки] должно быть рациональное число, т.е. 50.93 или 134.79.\n"
                       "Попробуйте заново, или введите /cancel, чтобы отменить внесение накладной.")
    
    processed_data = {"invoice_data": (invoice_number, date, cost), "product_data": []}

    product_lines = lines[1:]
    processed_data["product_data"] = list()
    for product_line in product_lines:
        product_data = product_line.strip().split("/")
        if product_line.strip() and len(product_data) != 4 and not re.match(product_regex, product_line):
            return False, (f"ОШИБКА: Неверный формат строки товара: '{product_line}'.\n\n"
                           "Правила:\n"
                           "1. Каждая строка товара должна быть в формате: "
                           "[Наименование товара]/[Количество]/[Закупочная стоимость]/[Цена продажи]/[Акционная цена].\n"
                           "2. В поле [Наименование товара] должно быть строка, т.е. 'Хризантема'.\n\n"
                           "Попробуйте заново, или введите /cancel, чтобы отменить внесение накладной.")
        if len(product_data) == 5:
            product_name, quantity, purchase_price, sale_price, promotion_price = product_data
        else:
            product_name, quantity, purchase_price, sale_price = product_data
            promotion_price = 0
        try:
            quantity = int(quantity)
            purchase_price = float(purchase_price)
            sale_price = float(sale_price)
            promotion_price = float(promotion_price)
        except ValueError:
            return False, ("ОШИБКА: Неверный формат полей [Количество], [Закупочная стоимость], "
                           f"[Цена продажи] или [Акционная цена] в строке: '{product_line}'.\n\n"
                           "Правила:\n"
                           "1. В поле [Количество] должно быть натуральное число, т.е. 50 или 1.\n"
                           "2. В поле [Закупочная стоимость], [Цена продажи] и [Акционная цена] должно быть рациональное число, т.е. 50.93 или 134.79.\n\n"
                           "Попробуйте заново, или введите /cancel, чтобы отменить внесение накладной.")
        processed_data["product_data"].append((product_name, quantity, purchase_price, sale_price, promotion_price))

    return True, processed_data

async def process_sell_data(sell_data: str):
    regex = r"(\d+)/(\d+)"

    header_match = re.match(regex, sell_data)
    if header_match:
        product_id, quantity= sell_data.split("/")
        try:
            product_id = int(product_id)
            quantity = int(quantity)
        except ValueError:
            return False, ("ОШИБКА: неверный формат полей [Идентификатор товара] или [Количество]\n\n"
                            "Правила:\n"
                            "1. В поле [Идентификатор товара] и [Количество] должно быть натуральное число.\n\n"
                            "Попробуйте заново, или введите /cancel для отмены продажи.")
        return True, (product_id, quantity)
    else:
        return False, ("ОШИБКА: неверный формат ввода данных. "
                       "Данные должны быть в формате [Идентификатор товара]/[Количество].\n\n"
                       "Попробуйте заново или нажмите /cancel для отмены продажи.")

async def process_composition_keywords(keywords: str):
    regex = r"^(?:[А-Яа-яЁё]+(?:\n|$))+"

    header_match = re.match(regex, keywords)
    if header_match:
        keywords_list = keywords.split("\n")
        return True, keywords_list
    else:
        return False, ("ОШИБКА: неверный формат ввода данных. "
                       "Ключевые слова должны располагаться по однму на каждой строке, "
                       "каждое слово не должно содержать специальных символов.\n\n"
                       "Попробуйте заново или нажмите /cancel для отмены продажи.")
    
async def process_composition_sell_data(sell_data: str):
    regex = r"^(?:Утиль/)?\d+/\d+/\d+(?:\.\d+)?(?:\n(?:Утиль/)?\d+/\d+/\d+(?:\.\d+)?)*$"

    processed_data = list()
    header_match = re.match(regex, sell_data, re.IGNORECASE)
    if header_match:
        sell_data_list = sell_data.split("\n")
        if len(sell_data_list) < 2:
            return False, ("ОШИБКА: Композиция не может состоять из одного товара, "
                           "попробуйте заново или нажмите /cancel для отмены продажи.")
        for item in sell_data_list:
            if len(item.split("/")) == 4:
                is_trash = True
                _, product_id, sold_pieces, sale_price = item.split("/")
            else:
                is_trash = False
                product_id, sold_pieces, sale_price = item.split("/")
            try:
                product_id = int(product_id)
                sold_pieces = int(sold_pieces)
                sale_price = float(sale_price)
            except ValueError:
                return False, ("ОШИБКА: неверный формат полей [Идентификатор товара], "
                               "[Количество для продажи] или [Цена продажи].\n\n"
                               "Правила:\n"
                               "1. В поле [Идентификатор товара] и [Количество для продажи] должно быть натуральное число.\n"
                               "2. В поле [Цена продажи] должно быть рациональное число.\n\n"
                               "Попробуйте заново, или введите /cancel для отмены продажи.")
            processed_data.append((is_trash, product_id, sold_pieces, sale_price))
        return True, processed_data
    else:
        return False, ("ОШИБКА: неверный формат ввода данных. "
                       "Данные для продажи должны иметь формат: "
                       "[Идентификатор товара]/[Количество для продажи]/[Цена продажи] и располагаться по одному на каждой строке.\n\n"
                       "Попробуйте заново или нажмите /cancel для отмены продажи.")
    
async def process_change_price_data(data: str):
    regex = r"^(?:\d+/\d+(?:\.\d+)?\n?)+$"

    processed_data = list()
    match = re.match(regex, data)
    if match:
        data_list = data.split("\n")
        if len(data_list) < 1:
            return False, ("ОШИБКА: Слишком мало данных, "
                           "попробуйте заново или нажмите /cancel для отмены изменения цены.")
        for item in data_list:
            product_id, new_price = item.split("/")
            try:
                product_id = int(product_id)
                new_price = float(new_price)
            except ValueError:
                return False, ("ОШИБКА: неверный формат полей [Идентификатор товара], [Новая цена продажи] или [Акционная цена].\n\n"
                                "Правила:\n"
                                "1. В поле [Идентификатор товара] должно быть натуральное число.\n"
                                "2. В поле [Новая цена продажи] или [Новая акционная цена] должно быть рациональное число.\n\n"
                                "Попробуйте заново, или введите /cancel для отмены добавления утиля.")
            processed_data.append((product_id, new_price))
        return True, processed_data
    else:
        return False, ("ОШИБКА: неверный формат ввода данных. "
                       "Данные для изменения цены должны иметь формат: "
                       "[Идентификатор товара]/[Новая цена продажи] или [Новая акционная цена] и располагаться по одному на каждой строке.\n\n"
                       "Попробуйте заново или нажмите /cancel для отмены добавления утиля.")

async def process_trash_data(trash_data: str):
    regex = r"^(?:\d+/\d+\n?)+$"

    processed_data = list()
    match = re.match(regex, trash_data)
    if match:
        trash_data_list = trash_data.split("\n")
        if len(trash_data_list) < 1:
            return False, ("ОШИБКА: Слишком мало данных, "
                           "попробуйте заново или нажмите /cancel для отмены продажи.")
        for item in trash_data_list:
            product_id, quantity = item.split("/")
            try:
                product_id = int(product_id)
                quantity = int(quantity)
            except ValueError:
                return False, ("ОШИБКА: неверный формат полей [Идентификатор товара] или [Количество]\n\n"
                                "Правила:\n"
                                "1. В поле [Идентификатор товара] и [Количество] должно быть натуральное число.\n\n"
                                "Попробуйте заново, или введите /cancel для отмены добавления утиля.")
            processed_data.append((product_id, quantity))
        return True, processed_data
    else:
        return False, ("ОШИБКА: неверный формат ввода данных. "
                       "Данные для утиля должны иметь формат: "
                       "[Идентификатор товара]/[Количество] и располагаться по одному на каждой строке.\n\n"
                       "Попробуйте заново или нажмите /cancel для отмены добавления утиля.")

async def dynamic_search(keyword: str, products: list, min_similarity=80.0):
    regex = r"^\w+$"
    result = bool(re.match(regex, keyword))
    if result:
        names = [product["name"] for product in products]
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, lambda: process.extract(query=keyword.lower(),
                                                                           choices=names,
                                                                           scorer=fuzz.partial_ratio,
                                                                           limit=None))
        filtered_results = [
            {
                "product":product, "similarity":similarity
            } 
            for product, similarity, _ in results if similarity >= min_similarity
        ]
        
        enhanced_results = []
        for res in filtered_results:
            matching_products = [
                item for item in products if item["name"] == res["product"]
            ]
            for match in matching_products:
                enhanced_results.append({
                    "id": match["id"],
                    "name": res["product"],
                    "date": match["date"],
                    "remaining_pieces": match["remaining_pieces"],
                    "lost_pieces": match["lost_pieces"],
                    "similarity": res["similarity"]
                })

        return True, enhanced_results
    else:
        return False, ("ОШИБКА: Введите одно слово без спец символов")