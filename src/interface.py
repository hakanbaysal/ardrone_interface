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

class Interface():
    ''' User Interface for controlling the AR.Drone '''

    def __init__(self):
        ''' Constructor for setting up the User Interface '''
    	# Initialize pygame
        pygame.init()
        
        # Initialize Clock
        self.clock = pygame.time.Clock()

        # Setup the main screen
        self.resolution = (640, 360) # This is the screen size of AR.Drone 2. Works also for AR.Drone 1
        self.screen     = pygame.display.set_mode( self.resolution )
        pygame.display.set_caption( 'NLR: AR.Drone Keyboard Interface' )

        # Setup the background
        self.background = pygame.Surface( self.screen.get_size() )
        self.background = self.background.convert()
        self.background.fill( (255, 255, 255) )

        # ROS Settings
        self.publisher_land           = rospy.Publisher(  '/ardrone/land',      Empty )
        self.publisher_takeOff        = rospy.Publisher(  '/ardrone/takeoff',   Empty )
        self.publisher_parameters     = rospy.Publisher(  '/cmd_vel',           Twist )
        self.subscriber_camera_front  = rospy.Subscriber( '/ardrone/front/image_raw',  Image, self.__callback )
        self.subscriber_camera_bottom = rospy.Subscriber( '/ardrone/bottom/image_raw', Image, self.__callback )
        self.parameters               = Twist()
        rospy.init_node( 'interface' )

        # AR.Drone Variables
        self.airborne = False
        self.speed    = 0.2
        self.image = None

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
                    elif event.key == pygame.K_MINUS:
                        new_speed = self.speed - 0.05
                        if new_speed >= -1:
                            self.speed = new_speed
                        print self.speed
                    elif event.key == pygame.K_EQUALS:
                        new_speed = self.speed + 0.05
                        if new_speed <= 1:
                            self.speed = new_speed
                        print self.speed
                    elif event.key == pygame.K_SPACE:
                        if self.airborne:
                            self.__land()
                            self.airborne = False
                        else:
                            self.__takeOff()
                            self.airborne = True
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
        self.screen.blit( image, (0, 0) )
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

if __name__ == '__main__':
    ''' Starts up the software '''
    print '\n---> Starting up driver!\n'
    ardrone_driver = Popen( ['rosrun', 'ardrone_autonomy', 'ardrone_driver'])
    print '\n---> Starting up NLR: AR.Drone Keyboard Inferface!\n'
    GUI = Interface()
    GUI.run()
    ardrone_driver.kill()
    print '\n---> Shutting down driver!\n'
    print '\n---> Ended Sucessfuly!\n'