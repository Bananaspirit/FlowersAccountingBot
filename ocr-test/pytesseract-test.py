import pytesseract
import cv2

# Load the image
image = cv2.imread('cut.jpg')
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# Extract text using Tesseract
text = pytesseract.image_to_string(gray, lang='rus')

print(text)
