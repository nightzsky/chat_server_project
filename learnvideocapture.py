import numpy as py
import cv2

#capture a video from the camera (mine is using laptop's webcam)
#convert into grayscale and then displaying it
#normally one camera will be connected, and therefore device index passed will be 0

#can capture frame-by-frame, but remember to release the capture at the end

def captureVideo():
    
    capturevid = cv2.VideoCapture(0)

    while(True):
        #capture frame-by-frame
        ret, frame = capturevid.read()

        #operations on the frames defined below
        #converting color into grayscale
        gray = cv2.cvtColor(frame,  cv2.COLOR_BGR2GRAY)
        # hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        #displaying the resulting frames
        #press q to quit
        #if dont want to use either grayscale image or hsv images
        #change second argument below to what you defined above in frame
        cv2.imshow('frame', gray)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    #when everything is done, release the capture
    capturevid.release()
    cv2.destroyAllWindows()