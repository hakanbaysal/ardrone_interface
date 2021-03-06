#!/usr/bin/env python
'''
############### NLR: AR.Drone Keyboard Interface ###############

Filename:       interface.py
Description:    This interface is a control interface for the AR.Drone 1/2.
                It depends on the ardrone_autonomy driver, which contains
                the AR.Drone SDK and implements the basic communication. This
                interface can be used to fly the AR.Drone
By:             Camiel Verschoor
Created:        22-10-2012

############### NLR: AR.Drone Keyboard Interface ###############
'''

# Libraries
import roslib; roslib.load_manifest('ardrone_interface')
import rospy
import pygame
import std_srvs.srv
import time
from subprocess import Popen
from pygame.locals import * 
from std_msgs.msg import *
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Image
from tld_msgs.msg import BoundingBox

class Interface():
    ''' User Interface for controlling the AR.Drone '''

    def __init__(self):
        ''' Constructor for setting up the User Interface '''
    	# Initialize pygame
        pygame.init()
        
        # Initialize Clock
        self.clock = pygame.time.Clock()

        # Setup the main screen
        self.resolution = (640, 460) # This is the screen size of AR.Drone 2. Works also for AR.Drone 1
        self.screen     = pygame.display.set_mode( self.resolution )
        pygame.display.set_caption( 'NLR: AR.Drone Keyboard Interface' )

        # Setup the background
        self.background = pygame.Surface( self.screen.get_size() )
        self.background = self.background.convert()
        self.background.fill( (255, 255, 255) )

        # Setup logo
        self.logo           = pygame.image.load( roslib.packages.get_pkg_dir('ardrone_interface')+ "/images/logo.png" ).convert()
        self.logo_rect      = self.logo.get_rect()
        self.logo_rect.left = 0
        self.logo_rect.top  = 360
	

        self.background.blit( self.logo, self.logo_rect )
        self.screen.blit( self.background, (0,0) )
        pygame.display.flip()

        # ROS Settings
        self.publisher_land           = rospy.Publisher(  '/ardrone/land',      Empty )
        self.publisher_takeOff        = rospy.Publisher(  '/ardrone/takeoff',   Empty )
	self.publisher_reset	      = rospy.Publisher(  '/ardrone/reset',     Empty ) #edited by Ardillo make a reset possible after over-tilt
        self.publisher_parameters     = rospy.Publisher(  '/cmd_vel',           Twist )
        self.subscriber_camera_front  = rospy.Subscriber( '/ardrone/front/image_raw',  Image, self.__callback ) # Front image
        self.subscriber_camera_bottom = rospy.Subscriber( '/ardrone/bottom/image_raw', Image, self.__callback ) # Bottom image
        self.subscriber_tracker       = rospy.Subscriber( '/tld_tracked_object', BoundingBox, self.__callback_tracker ) # Tracker
        self.parameters               = Twist()
        rospy.init_node( 'interface' )

        # AR.Drone Variables
        self.airborne = False
        self.speed    = 0.2
        self.image    = None
	self.manual_flightmode = True
	self.confidence = None 	#confidence variable by Ardillo, has to be in front of ROS Settings.
	self.header_seq = None
	self.old_seq = None

        # Tracking box
        self.tracking_box = pygame.Rect(641, 461, 1, 1)
	self.center_box = pygame.Rect((320-64), (230-46), 128, 92)

    def __del__(self):
        ''' Destructor of the User Interface'''
        pygame.quit()

    def run(self):
        ''' Main loop, which refreshes the screen and handles User Input '''
        print "Starting NLR: AR.Drone Keyboard Interface"
        done = False

        while not(done):
            for event in pygame.event.get():
                # Check if window is quit
                if event.type == pygame.QUIT:
                    done = True
                    break
                # Check if key is pressed
                elif event.type == pygame.KEYDOWN:
                    if   event.key == pygame.K_UP:
                        self.parameters.linear.x = self.speed
                    elif event.key == pygame.K_LEFT:
                        self.parameters.linear.y = self.speed
                    elif event.key == pygame.K_DOWN:
                        self.parameters.linear.x = -self.speed
                    elif event.key == pygame.K_RIGHT:
                        self.parameters.linear.y = -self.speed
                    elif event.key == pygame.K_w:
                        self.parameters.linear.z = self.speed
                    elif event.key == pygame.K_a:
                        self.parameters.angular.z = self.speed
                    elif event.key == pygame.K_s:
                        self.parameters.linear.z = -self.speed
                    elif event.key == pygame.K_d:
                        self.parameters.angular.z = -self.speed
                    elif event.key == pygame.K_c:
                        self.__toggleCam()
		    elif event.key == pygame.K_r: #edited by Ardillo making reset function
			self.__reset()
                    elif event.key == pygame.K_MINUS:
                        self.__switchSpeed( -0.01 ) #edited by Ardillo making it more sensible
                        print self.speed
                    elif event.key == pygame.K_EQUALS:
                        self.__switchSpeed( 0.01 ) #edited by Ardillo making it more sensible
                        print self.speed
                    elif event.key == pygame.K_SPACE:
                        if self.airborne:
                            self.__land()
                            self.airborne = False
                        else:
                            self.__takeOff()
                            self.airborne = True
		    elif event.key == pygame.K_m: # Boolean toggle by Ardillo
			self.manual_flightmode = not self.manual_flightmode
			print "Manual_flightmode =",self.manual_flightmode
			if self.manual_flightmode == False:
			    self.__trackObject()
			    print "Manual_flightmode =",self.manual_flightmode
			
                # Check if key is released.
                elif event.type == pygame.KEYUP:
                    if   event.key == pygame.K_UP:
                        self.parameters.linear.x = 0
                    elif event.key == pygame.K_LEFT:
                        self.parameters.linear.y = 0
                    elif event.key == pygame.K_DOWN:
                        self.parameters.linear.x = 0
                    elif event.key == pygame.K_RIGHT:
                        self.parameters.linear.y = 0
                    elif event.key == pygame.K_w:
                        self.parameters.linear.z = 0
                    elif event.key == pygame.K_a:
                        self.parameters.angular.z = 0
                    elif event.key == pygame.K_s:
                        self.parameters.linear.z = 0
                    elif event.key == pygame.K_d:
                        self.parameters.angular.z = 0

            self.publisher_parameters.publish( self.parameters )
            self.__draw()
            self.clock.tick(30)

    def __draw(self):
        ''' Draws the camera feed on the screen '''
        if self.image == None:
            return
 	image = pygame.image.fromstring( self.image.data, (self.image.width, self.image.height), "RGB" )
        self.background.blit( image, (0, 0) )
	if self.old_seq == self.header_seq: # don't show old rectangles
	    self.tracking_box = pygame.Rect(641, 461, 1, 1)
	self.old_seq = self.header_seq
        pygame.draw.rect( self.background, (0, 0, 255), self.tracking_box, 2 )
       	pygame.draw.rect( self.background, (100, 100, 100), self.center_box, 1 )
        self.screen.blit( self.background, (0, 0) )
        pygame.display.flip()

    def __toggleCam(self):
        ''' Switches between camera feeds of the AR.Drone '''
        rospy.wait_for_service( 'ardrone/togglecam' )
        try:
            toggle = rospy.ServiceProxy( 'ardrone/togglecam', std_srvs.srv.Empty )
            toggle()
        except rospy.ServiceException, e:
            print "Service call failed: %s"%e

    def __takeOff(self):
        ''' Take off signal for AR.Drone '''
        print "Taking off"
        self.publisher_takeOff.publish( Empty() )

    def __land(self):
        ''' Landing signal for AR.Drone '''
        print "Landing"
        self.publisher_land.publish( Empty() )

    def __callback(self, raw_image):
        ''' Callback function for the camera feed '''
        self.image = raw_image

    def __callback_tracker(self, tracking_box):
        ''' Callback function for the rectangle'''
	self.tracking_box = pygame.Rect( tracking_box.x, tracking_box.y, tracking_box.width, tracking_box.height )
	self.confidence = tracking_box.confidence # got the confidence variable, for future use. By Ardillo
	self.header_seq = tracking_box.header.seq

    def __switchSpeed( self, speed ):
        new_speed = self.speed + speed
        if new_speed >= -1 and new_speed <= 1:
            self.speed = new_speed

    def __reset(self):				# edited by Ardillo making reset function
	''' Reset signal for AR.Drone '''
	print "Resetting"
	self.publisher_reset.publish( Empty() )

    def __trackObject(self):			# making an automated flight procedure by Ardillo, NO CONTROLS POSSIBLE EXCEPT EMERGENCY RESET
	''' Track the target '''
	print "In autonomous_flightmode"
	done = False
	while not(done):

		# check location of Bounding box.
	    	if self.tracking_box.x <= 640 and self.tracking_box.y <= 460:
	            #print "within marge, x = " , self.tracking_box.x , " y = " , self.tracking_box.y
		    self.center_tracking_box_x = self.tracking_box.x + (self.tracking_box.width / 2)
		    self.center_tracking_box_y = self.tracking_box.y + (self.tracking_box.height / 2)

		    if self.old_seq != self.header_seq:	
		    	if self.center_tracking_box_x < self.center_box.x:
		            print "go Right !"
		            self.parameters.linear.y = -self.speed
		    	if self.center_tracking_box_x > (self.center_box.x + self.center_box.width):
		            print "go Left !"
		            self.parameters.linear.y = self.speed
		    	if self.center_tracking_box_y < self.center_box.y:
		            print "go Up !"
		            self.parameters.linear.x = self.speed
		    	if self.center_tracking_box_y > (self.center_box.y + self.center_box.height):
		            print "go Down !"
		            self.parameters.linear.x = -self.speed
		    
		    #self.old_seq = self.header_seq
		    self.publisher_parameters.publish( self.parameters )
		    self.clock.tick(30)
                    self.parameters.linear.y = 0
                    self.parameters.linear.x = 0
                    

	        for event in pygame.event.get():
        	    # Check if window is quit
        	    if event.type == pygame.QUIT:
        	        done = True
        	        break
        	    # Check if key is pressed
        	    elif event.type == pygame.KEYDOWN:
		        if  event.key == pygame.K_m:
			    print "Back to manual_flightmode"
			    self.manual_flightmode = not self.manual_flightmode
			    return
		        elif event.key == pygame.K_r: 
			    self.__reset()

	        self.__draw()


	    
	

if __name__ == '__main__':
    ''' Starts up the software '''
    print '\n---> Starting up driver!\n'
    ardrone_driver = Popen( ['rosrun', 'ardrone_autonomy', 'ardrone_driver'])
    print '\n---> Starting up NLR: AR.Drone Keyboard Inferface!\n'
    GUI = Interface()
    GUI.run()
    ardrone_driver.kill()
    print '\n---> Shutting down driver!\n'
    print '\n---> Ended Successfully!\n'
