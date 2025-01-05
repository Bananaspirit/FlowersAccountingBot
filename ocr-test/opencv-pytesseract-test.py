import cv2
import numpy as np
import pytesseract
import pandas as pd

# Function to preprocess the image
def preprocess_image(image_path):
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    # _, binary_image = cv2.threshold(image, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    binary_image = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, blockSize=11, C=1)
    # binary_image = cv2.bitwise_not(binary_image)
    cv2.imwrite('pics/debug_binary.png', binary_image)
    return binary_image

# Function to detect vertical and horizontal lines
def detect_lines(binary_image):
    kernel_len = binary_image.shape[1] // 40
    
    # Detect vertical lines
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_len))
    vertical_lines = cv2.erode(binary_image, vertical_kernel, iterations=3)
    vertical_lines = cv2.dilate(vertical_lines, vertical_kernel, iterations=3)
    cv2.imwrite("pics/vertical.jpg", vertical_lines)

    # Detect horizontal lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_len, 1))
    horizontal_lines = cv2.erode(binary_image, horizontal_kernel, iterations=3)
    horizontal_lines = cv2.dilate(horizontal_lines, horizontal_kernel, iterations=3)
    cv2.imwrite("pics/horizontal.jpg", horizontal_lines)

    # Combine lines
    table_structure = cv2.addWeighted(vertical_lines, 0.5, horizontal_lines, 0.5, 0.0)
    return table_structure

# Function to extract contours for table cells
def extract_table_cells(table_structure):
    contours, _ = cv2.findContours(table_structure, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    cells = []

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w > 30 and h > 20:  # Filter out small contours
            cells.append((x, y, w, h))

    # Sort cells first by rows, then by columns
    cells = sorted(cells, key=lambda b: (b[1], b[0]))
    return cells

# Function to extract text from cells
def extract_text_from_cells(image, cells):
    extracted_data = []
    for (x, y, w, h) in cells:
        cell = image[y:y+h, x:x+w]
        cell = cv2.bitwise_not(cell)
        cell_text = pytesseract.image_to_string(cell, lang="rus", config="--psm 6")
        extracted_data.append(cell_text.strip())
    return extracted_data

# Function to organize extracted text into a structured DataFrame
def organize_data_to_dataframe(extracted_data, cells):
    rows = []
    current_row = []
    last_y = cells[0][1]

    for i, (x, y, w, h) in enumerate(cells):
        if abs(y - last_y) > 10:  # New row
            rows.append(current_row)
            current_row = []
            last_y = y
        current_row.append(extracted_data[i])

    if current_row:
        rows.append(current_row)

    df = pd.DataFrame(rows)
    return df

# Main function to process an image and save the result as an Excel file
def process_image_to_excel(image_path, output_excel_path):
    binary_image = preprocess_image(image_path)
    table_structure = detect_lines(binary_image)
    cells = extract_table_cells(table_structure)
    extracted_data = extract_text_from_cells(binary_image, cells)
    df = organize_data_to_dataframe(extracted_data, cells)
    df.to_excel(output_excel_path, index=False)
    print(f"Data saved to {output_excel_path}")

# Example usage
if __name__ == "__main__":
    image_path = "test_correct.jpg"  # Replace with your image path
    output_excel_path = "pics/output.xlsx"
    process_image_to_excel(image_path, output_excel_path)

# import cv2
# import numpy as np
# import pytesseract
# import pandas as pd

# # Read the image
# image = cv2.imread("test_correct.jpg", cv2.IMREAD_GRAYSCALE)

# # Thresholding to get binary image
# _, binary = cv2.threshold(image, 230, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
# cv2.imwrite("debug_binary.jpg", binary)

# kernel_len = np.array(image).shape[1] // 100

# # Detect horizontal lines
# horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_len, 1))
# horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)

# # Detect vertical lines
# vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_len))
# vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)

# # Combine the lines to find the table structure
# table_structure = cv2.add(horizontal_lines, vertical_lines)

# # Find contours of the table cells
# contours, _ = cv2.findContours(table_structure, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# # Sort contours top-to-bottom and left-to-right
# def sort_contours(contours):
#     bounding_boxes = [cv2.boundingRect(c) for c in contours]
#     contours_sorted = sorted(zip(contours, bounding_boxes), key=lambda x: (x[1][1], x[1][0]))
#     return [c[0] for c in contours_sorted]

# contours = sort_contours(contours)

# # Extract and OCR each cell
# data = []
# debug_image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
# for contour in contours:
#     x, y, w, h = cv2.boundingRect(contour)
#     if w > 10 and h > 10:  # Filter small contours
#         cell = image[y:y+h, x:x+w]
#         text = pytesseract.image_to_string(cell, lang='rus', config="--psm 11")  # Set PSM for uniform text
#         data.append((y, x, text.strip()))
#         cv2.rectangle(debug_image, (x, y), (x+w, y+h), (0, 255, 0), 2)
# cv2.imwrite("debug_cells.jpg", debug_image)

# # Group text into rows based on the Y-coordinate
# rows = {}
# for y, x, text in data:
#     rows.setdefault(y, []).append((x, text))

# # Sort rows and cells
# sorted_rows = [rows[key] for key in sorted(rows.keys())]
# sorted_cells = [[text for _, text in sorted(row)] for row in sorted_rows]

# # Convert to DataFrame and Save to Excel
# df = pd.DataFrame(sorted_cells)
# df.to_excel("output.xlsx", index=False, header=False)