import cv2

# Open the Pi camera
cap = cv2.VideoCapture(0)  # Use 0 for the default camera

if not cap.isOpened():
    print("Error: Could not open camera.")
    exit()

# Capture a single frame
ret, frame = cap.read()

if ret:
    # Display the frame
    cv2.imshow("Pi Camera Test", frame)
    cv2.imwrite("test_image.jpg", frame)  # Save the image

    # Wait for a key press and close window
    cv2.waitKey(0)
    cv2.destroyAllWindows()
else:
    print("Error: Could not capture frame.")

# Release the camera
cap.release()
