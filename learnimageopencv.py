import numpy as py
import cv2

#cv2.IMREAD_COLOR (1, default): loads a color image, any transparency of image neglected
#cv2.IMREAD_GRAYSCALE (0): loads image in grayscale
#cv2.IMREAD_UNCHANGED (-1): loads image as such including alpha channel
#can pass integers rather than typing the whole thing

color = cv2.imread('mockingspongebob.png', 1)
grayscale = cv2.imread('mockingspongebob.png', 0)
nochange = cv2.imread('mockingspongebob.png', -1)

def showimage():
    cv2.imshow('color', color)
    cv2.imshow('grayscale', grayscale)
    cv2.imshow('nochange', nochange)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
#cv2.waitKey() shows keyboard binding function. param is taken in milliseconds.
#if set to 0, will wait indefinitely for a key stroke


#by default, flag is cv2.WINDOW_AUTOSIZE
#if specify flag to be cv2.WINDOW_NORMAL, window can be resized
def showresizeableimage():
    cv2.namedWindow('resizeablecolor', cv2.WINDOW_NORMAL)
    cv2.imshow('resizeablecolor', color)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

#saving an image
#image will be saved in PNG format in working directory
def saveimage():
    cv2.imshow('grayscale', grayscale)
    cv2.imwrite('mockingspongebobgray.png', grayscale)


if __name__ == "__main__":
    # showimage()
    # showresizeableimage()
    saveimage()