import openpyxl

wb = openpyxl.load_workbook('excel/Шаблон FlowersBusiness.xlsx', keep_vba=True)

sheet = wb["Статистика за месяц"]

cellD6 = sheet["D6"]

if isinstance(cellD6.value, (int, float)):  # If it's a number
    new_value = 16  # Value you want to add
    cellD6.value += new_value  # Add the new value to the existing one
    print(f"New value in D6: {cellD6.value}")
else:
    print(f"Cell D6 does not contain a number. Current value: {cellD6.value}")

wb.save('excel/updated_Flowers_file.xlsx')