import numpy as np
import cv2

#tried and tested, not too sure why .mp4 does not work, but so far only tried .avi and .mp4
capturevid = cv2.VideoCapture('testvideo.avi')

#same thing as for video capture, if you want to display the exact same content as your video
#make sure to change second argument of cv2.imshow() to frame
#similarly, ord('q') is press q to quit
while(capturevid.isOpened()):
    ret, frame = capturevid.read()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    cv2.imshow('frame', gray)
    if cv2.waitKey(25) & 0xFF == ord('q'):
        break

capturevid.release()
cv2.destroyAllWindows()

def captureandsavevid():
    capturevid = cv2.VideoCapture(0)
    fourcc = cv2.VideoWriter_fourcc(*'DIVX')
    outvid = cv2.VideoWriter('testvideoout.avi', fourcc, 20.0, (640, 480))

    while(capturevid.isOpened()):
        ret, frame = capturevid.read()
        if ret == True:
            frame = cv2.flip(frame, 0)
            out.write(frame)
            cv2.imshow('frame', frame)
            if cv2.waitKey(25) & 0xFF == ord('q'):
                break
        else:
            break

    capturevid.release()
    outvid.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    capturevid
    # captureandsavevid()