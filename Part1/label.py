# -*- coding: utf-8 -*-
import cv2
import numpy as np
import math
import datetime
label = 0
y_x_coord = []

class PanZoomWindow(object):
    """ Controls an OpenCV window. Registers a mouse listener so that:
        1. right-dragging up/down zooms in/out
        2. right-clicking re-centers
        3. trackbars scroll vertically and horizontally
    You can open multiple windows at once if you specify different window names.
    You can pass in an onLeftClickFunction, and when the user left-clicks, this
    will call onLeftClickFunction(y,x), with y,x in original image coordinates."""

    def __init__(self, img, windowName = 'PanZoomWindow', onLeftClickFunction = None):
        self.WINDOW_NAME = windowName
        self.H_TRACKBAR_NAME = 'x'
        self.V_TRACKBAR_NAME = 'y'
        self.img = img
        self.onLeftClickFunction = onLeftClickFunction
        self.TRACKBAR_TICKS = 1000
        self.panAndZoomState = PanAndZoomState(img.shape, self)
        self.lButtonDownLoc = None
        self.mButtonDownLoc = None
        self.rButtonDownLoc = None
        cv2.namedWindow(self.WINDOW_NAME, cv2.WINDOW_NORMAL)
        self.redrawImage()
        cv2.setMouseCallback(self.WINDOW_NAME, self.onMouse)
        cv2.createTrackbar(self.H_TRACKBAR_NAME, self.WINDOW_NAME, 0, self.TRACKBAR_TICKS, self.onHTrackbarMove)
        cv2.createTrackbar(self.V_TRACKBAR_NAME, self.WINDOW_NAME, 0, self.TRACKBAR_TICKS, self.onVTrackbarMove)
    def onMouse(self,event, x,y,_ignore1,_ignore2):
        """ Responds to mouse events within the window.
        The x and y are pixel coordinates in the image currently being displayed.
        If the user has zoomed in, the image being displayed is a sub-region, so you'll need to
        add self.panAndZoomState.ul to get the coordinates in the full image."""
        global label
        global y_x_coord
        if event == cv2.EVENT_MOUSEMOVE:
            return
        elif event == cv2.EVENT_RBUTTONDOWN:
            #record where the user started to right-drag
            self.mButtonDownLoc = np.array([y,x])
        elif event == cv2.EVENT_RBUTTONUP and self.mButtonDownLoc is not None:
            #the user just finished right-dragging
            dy = y - self.mButtonDownLoc[0]
            pixelsPerDoubling = 0.2*self.panAndZoomState.shape[0] #lower = zoom more
            changeFactor = (1.0+abs(dy)/pixelsPerDoubling)
            changeFactor = min(max(1.0,changeFactor),5.0)
            if changeFactor < 1.05:
                dy = 0 #this was a click, not a draw. So don't zoom, just re-center.
            if dy > 0: #moved down, so zoom out.
                zoomInFactor = 1.0/changeFactor
            else:
                zoomInFactor = changeFactor
#            print "zoomFactor:",zoomFactor
            self.panAndZoomState.zoom(self.mButtonDownLoc[0], self.mButtonDownLoc[1], zoomInFactor)
        elif event == cv2.EVENT_LBUTTONDOWN:
            #the user pressed the left button.
            coordsInDisplayedImage = np.array([y,x])
            if np.any(coordsInDisplayedImage < 0) or np.any(coordsInDisplayedImage > self.panAndZoomState.shape[:2]):
                print "you clicked outside the image area"
            else:
                label+=1
                #print "you clicked on",coordsInDisplayedImage,"within the zoomed rectangle"
                coordsInFullImage = self.panAndZoomState.ul + coordsInDisplayedImage
                print "Label: ",label, " Coordinates: ",coordsInFullImage
                y_x_coord.append(coordsInFullImage)
                # Draw a red closed circle
                cv2.circle(self.img,(coordsInFullImage[1],coordsInFullImage[0]), 10, (0,0,255), -1)
                font = cv2.FONT_HERSHEY_SIMPLEX
                cv2.putText(self.img,str(label),(coordsInFullImage[1],coordsInFullImage[0] - 10), font, 1,(255,255,0),2)

                cv2.imshow("img",self.img)
                #self.img[y-30:y+30,x-30:x+30] = [255,255,255]
                #print "this pixel holds ",self.img[coordsInFullImage[0],coordsInFullImage[1]]
                if self.onLeftClickFunction is not None:
                    self.onLeftClickFunction(coordsInFullImage[0],coordsInFullImage[1])
        #you can handle other mouse click events here
    def onVTrackbarMove(self,tickPosition):
        self.panAndZoomState.setYFractionOffset(float(tickPosition)/self.TRACKBAR_TICKS)
    def onHTrackbarMove(self,tickPosition):
        self.panAndZoomState.setXFractionOffset(float(tickPosition)/self.TRACKBAR_TICKS)
    def redrawImage(self):
        pzs = self.panAndZoomState
        cv2.imshow(self.WINDOW_NAME, self.img[pzs.ul[0]:pzs.ul[0]+pzs.shape[0], pzs.ul[1]:pzs.ul[1]+pzs.shape[1]])

class PanAndZoomState(object):
    """ Tracks the currently-shown rectangle of the image.
    Does the math to adjust this rectangle to pan and zoom."""
    MIN_SHAPE = np.array([50,50])
    def __init__(self, imShape, parentWindow):
        self.ul = np.array([0,0]) #upper left of the zoomed rectangle (expressed as y,x)
        self.imShape = np.array(imShape[0:2])
        self.shape = self.imShape #current dimensions of rectangle
        self.parentWindow = parentWindow
    def zoom(self,relativeCy,relativeCx,zoomInFactor):
        self.shape = (self.shape.astype(np.float)/zoomInFactor).astype(np.int)
        #expands the view to a square shape if possible. (I don't know how to get the actual window aspect ratio)
        self.shape[:] = np.max(self.shape)
        self.shape = np.maximum(PanAndZoomState.MIN_SHAPE,self.shape) #prevent zooming in too far
        c = self.ul+np.array([relativeCy,relativeCx])
        self.ul = c-self.shape/2
        self._fixBoundsAndDraw()
    def _fixBoundsAndDraw(self):
        """ Ensures we didn't scroll/zoom outside the image.
        Then draws the currently-shown rectangle of the image."""
#        print "in self.ul:",self.ul, "shape:",self.shape
        self.ul = np.maximum(0,np.minimum(self.ul, self.imShape-self.shape))
        self.shape = np.minimum(np.maximum(PanAndZoomState.MIN_SHAPE,self.shape), self.imShape-self.ul)
#        print "out self.ul:",self.ul, "shape:",self.shape
        yFraction = float(self.ul[0])/max(1,self.imShape[0]-self.shape[0])
        xFraction = float(self.ul[1])/max(1,self.imShape[1]-self.shape[1])
        cv2.setTrackbarPos(self.parentWindow.H_TRACKBAR_NAME, self.parentWindow.WINDOW_NAME,int(xFraction*self.parentWindow.TRACKBAR_TICKS))
        cv2.setTrackbarPos(self.parentWindow.V_TRACKBAR_NAME, self.parentWindow.WINDOW_NAME,int(yFraction*self.parentWindow.TRACKBAR_TICKS))
        self.parentWindow.redrawImage()
    def setYAbsoluteOffset(self,yPixel):
        self.ul[0] = min(max(0,yPixel), self.imShape[0]-self.shape[0])
        self._fixBoundsAndDraw()
    def setXAbsoluteOffset(self,xPixel):
        self.ul[1] = min(max(0,xPixel), self.imShape[1]-self.shape[1])
        self._fixBoundsAndDraw()
    def setYFractionOffset(self,fraction):
        """ pans so the upper-left zoomed rectange is "fraction" of the way down the image."""
        self.ul[0] = int(round((self.imShape[0]-self.shape[0])*fraction))
        self._fixBoundsAndDraw()
    def setXFractionOffset(self,fraction):
        """ pans so the upper-left zoomed rectange is "fraction" of the way right on the image."""
        self.ul[1] = int(round((self.imShape[1]-self.shape[1])*fraction))
        self._fixBoundsAndDraw()

if __name__ == "__main__":
    infile = "./floor3_sml.jpg"
    myImage = cv2.imread(infile,cv2.CV_LOAD_IMAGE_COLOR)
    #cv2.circle(myImage,(200,200), 40, (0,0,255), -1)


    window = PanZoomWindow(myImage, "test window")
    key = -1
    k = cv2.waitKey(0)
    # while key != ord('q') and key != 27: # 27 = escape key
    #     #the OpenCV window won't display until you call cv2.waitKey()
    #     key = cv2.waitKey(5) #User can press 'q' or ESC to exit.

    if k == 27:         # wait for ESC key to exit
        cv2.destroyAllWindows()
    elif k == ord('s'): # wait for 's' key to save and exit
        cv2.imwrite('marked_'+datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y")+'.jpg',myImage)

        # for itr in y_x_coord:
            # print itr
        fp = open("coordinates_"+datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y")+".txt", "w")

        l=len(y_x_coord)
        next_ = None
        for index, obj in enumerate(y_x_coord):
            fp.write("%d %d " % (obj[0],obj[1]))
            if index < (l-1):
                next_ = y_x_coord[index + 1]
                displacement = (math.sqrt((obj[0] - next_[0])**2 + (obj[1] - next_[1])**2))*0.033917
                fp.write("%f m\n" % displacement)


        fp.close()

        cv2.destroyAllWindows()
