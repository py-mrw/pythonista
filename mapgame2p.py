# WindowNode is a prototype 2 player view of a single map by @mr_w 
# This file is a demonstration of WindowNode
#
# map templated from jsbain
#		https://gist.github.com/jsbain/7a1a3c1b0d28c752cba8f5420255dfe6
# basic scrolling example was by Dalorbi on the forums at:
#   http://omz-software.com/pythonista/forums/discussion/213/scrolling-in-scene-module/p1
# inertial scrolling after prior art by hroe 
#		https://gist.github.com/henryroe/6724117

from scene import *
import sound
import random
import math
import numpy
from math import exp
import datetime
import copy
import console

A = Action

mapscaler = 1.2
mapscaler_max = 10
mapscaler_min = 0.1

velocity_decay_timescale_seconds = 0.4
max_retained_touch_points = 6
min_velocity_points_per_second = 50	

water_shader = '''
precision highp float;
varying vec2 v_tex_coord;
uniform sampler2D u_texture;
uniform float u_time;
void main(void) {
	  vec4 color = vec4(1.3,1.3,1.3,1.0);
    vec2 p = -1.0 + v_tex_coord;
    float len = length(p);
    vec2 uv = v_tex_coord + (p/len) * 1.0 * cos(len*50.0 - u_time*10.0) * 0.01;
    gl_FragColor = texture2D(u_texture,uv) * color;
}
'''

mapsprites=['plc:Brown_Block','plc:Dirt_Block','plc:Grass_Block','plc:Plain_Block','plc:Water_Block']
def choose_random_node():
	tx=random.choice(mapsprites)
	sn=SpriteNode(tx)
	sn.image = tx
	if (tx == 'plc:Water_Block'):
		sn.shader=Shader(water_shader)
	return sn

treesprites=['plc:Tree_Tall','plc:Tree_Short','plc:Tree_Ugly']
def choose_random_tree():
	tx=random.choice(treesprites)
	sn=SpriteNode(tx)
	sn.image = tx
	return sn
	
class MapNode(Node):
	def __init__(self, size):
		'''create a map, randomly filled with sprites
		size is tuple containg row,col number of tiles'''
		self.map=[[choose_random_node() for i in range(size[1])] for j in range(size[0])]
		self.trees=[]
		r=0
		for row in self.map:
			r+=1
			c=0
			for col in row:
				c+=1
				col.position=(c*col.size.width, r*(row[0].size.height-40))
				col.z_position=-r
				self.add_child(col)
				if (col.image != 'plc:Water_Block' and random.random()<0.1):
					self.trees.append(choose_random_tree())
					self.trees[-1].position = (c*col.size.width, r*(row[0].size.height-40)+25)
					self.trees[-1].z_position=10000-self.trees[-1].position[1]-1
					self.add_child(self.trees[-1])
					
		self.tile_w = self.map[0][0].size.width
		self.tile_h = self.map[0][0].size.height-40
		self.player1=SpriteNode('plc:Character_Princess_Girl')
		self.player2=SpriteNode('plc:Character_Boy')
		self.rock=SpriteNode('plc:Rock')
		self.size=self.bbox
		self.player1.position=self.tile_w*10, self.tile_h*10.33
		self.player1.z_position = 10000-self.player1.position[1]
		self.player2.position=self.tile_w*20, self.tile_h*15.33
		self.player2.z_position = 10000-self.player2.position[1]
		self.add_child(self.player1)
		self.add_child(self.player2)
		self.scale=mapscaler**3
		
# class WindowNode
#
# Create a new view which is a rectangular window on an existing sprite node
#	 - spritenode : The existing sprite node
#	 - position   : A Vector2 that is the origin of the window, within the existing sprite node
#	 - size       : A Vector2 that is the size of the window 
# Note that the scale is originally the scale of the existing sprite node, but is deliberately
# not kept in synch, since this is an independent view.
#
# The refresh() function should be called from scene.update(), since this view needs to be refreshed
# every update if you want any shaders to work properly.
#
# To reposition the origin, simply set render_position, or you can use move_to() if you want a simple
# animation effect as you move to the new position
#
class WindowNode(SpriteNode):
	def __init__(self, spritenode, position, size, **kwargs):
		self.spritenode = spritenode
		self.render_position = Vector2(position[0], position[1])
		self.render_size = Vector2(size[0], size[1])
		self.render_rect = Rect(position[0], position[1], size[0]/spritenode.scale, size[1]/spritenode.scale)
		texture = spritenode.render_to_texture(self.render_rect)
		super(WindowNode, self).__init__(texture, size, **kwargs)
		self.scale = self.spritenode.scale
		self.animating = 0
		
	def move_to(self, newpos, t, dt):
		if self.animating == 1:
			self.render_position = self.oldpos + self.deltapos
		self.oldpos = self.render_position
		self.deltapos =  Vector2(newpos[0],newpos[1]) - self.render_position
		self.animating = 1
		self.t_start = t
		self.dt = dt
		
	def refresh(self, t):
		if (self.animating):
			progress = (t-self.t_start)/self.dt
			if (progress >= 1.0):
				progress = 1.0
				self.animating = 0
			self.render_position = self.oldpos + self.deltapos * progress
		self.texture = self.spritenode.render_to_texture((self.render_position[0], self.render_position[1], self.render_size[0]/self.scale, self.render_size[1]/self.scale))
		 	
class JoypadNode(Node):
	def __init__(self,xpos,xoffset, ypos, yoffset, icon):
		self.joyring=SpriteNode('emj:Red_Ring', scale = 3.0)
		self.joyring.position = (0,0)
		self.setposition(xpos, xoffset, ypos, yoffset)
		self.size = self.joyring.size*3.0
		self.add_child(self.joyring)
		self.padicon=SpriteNode(icon, color = 'black')
		self.padicon.position = self.joyring.position+(0,10)
		self.add_child(self.padicon)
	
	def readout(self, point):
		joypsn = point - self.position
		joysize = self.size[0]/2 # Ring radius
		joydist = abs(joypsn)
		if joydist > joysize: # Keep going if the finger slips off the joypad
			joypsn = joypsn * joysize / joydist
			joydist = joysize
		self.indicator(joypsn/10.0) # Visual indication only
		px = numpy.clip(int (joypsn[0]/(joysize/6)), -1, 1) # The inner sixth is 'off'
		py = numpy.clip(int (joypsn[1]/(joysize/6)), -1, 1)
		if (px != 0 or py != 0):
			dt = 1.0*(1-min(5/6,joydist/joysize))*((abs(px)+abs(py))**0.5) # Outer 1/6 is 'max'
		else:
			dt = 0
		return px, py, dt
		
	def indicator(self, delta_xy):
		self.padicon.position = self.joyring.position+(0,10)+delta_xy

	def setposition(self, xpos, xoffset, ypos, yoffset):
		self.position = (xpos+xoffset*2*self.joyring.size[0], ypos+yoffset*2*self.joyring.size[1])
		
class DividerNode (ShapeNode):
	def __init__(self, sz):
		self.node = None
		self.setposition(sz)
		
	def setposition(self, sz):
		if self.node is not None:
			self.node.remove_from_parent()
		c = 22
		w = c*sz[0]/1366
		pi = 3.1415926536
		height = sz[1]+1
		self.divider = ui.Path()
		self.divider.line_width = 1.0
		self.divider.move_to(-c-w,0)
		self.divider.add_arc(-c-w,c,c,3*pi/2,0,-1)
		self.divider.line_to(-w,height-c)
		self.divider.add_arc(-c-w,height-c,c,0,pi/2,-1)
		self.divider.line_to(c+w,height)
		self.divider.add_arc(c+w,height-c,c,pi/2,pi,-1)
		self.divider.line_to(w,c)
		self.divider.add_arc(c+w,c,c,pi,3*pi/2,-1)
		self.divider.line_to(-c-w,0)
		self.divider.fill()
		self.divider.stroke()
		self.node = ShapeNode(self.divider, fill_color='black', stroke_color='black')
		self.add_child(self.node)
		self.node.position=sz/2
		
class MyScene (Scene):
	def setup(self):
		self.mapnode=MapNode([30,40])
		self.splitscreennode1 = EffectNode((0,0))
		self.splitscreennode1.crop_rect=(0,0,self.size[0]/2,self.size[1])
		self.splitscreennode1.size = Size(self.size[0]/2,self.size[1])
		self.splitscreennode2 = WindowNode(self.mapnode, (0,0), (self.size[0]/2,self.size[1]))
		self.splitscreennode2.anchor_point = Vector2(0.0,1.0)
		
		self.add_child(self.splitscreennode1)
		self.add_child(self.splitscreennode2)
		self.splitscreennode1.add_child(self.mapnode)	
		self.dividernode = DividerNode(self.size)
		self.add_child(self.dividernode)
		
		self.mapnode.position = self.splitscreennode1.size/2-self.mapnode.player1.position*self.mapnode.scale
		
		#self.size=self.bbox
		
		self.joypad1=JoypadNode(0,1,0,1,'plc:Character_Princess_Girl')
		self.add_child(self.joypad1)
		self.joypad2=JoypadNode(self.size[0],-1,0,1,'plc:Character_Boy')
		self.add_child(self.joypad2)
		rectpath = ui.Path.rounded_rect(0,0,50,150,25)
		rectpath.line_width = 8
		self.controlpad1=ShapeNode(path=rectpath, fill_color=(0.5,0.5,0.5,0.75), stroke_color='red')
		self.controlpad1.position = (255,self.joypad1.position[1])
		self.add_child(self.controlpad1)
		self.controlpad2=ShapeNode(path=rectpath, fill_color=(0.5,0.5,0.5,0.75), stroke_color='red')
		self.controlpad2.position = (self.size[0]-255,self.joypad2.position[1])
		self.add_child(self.controlpad2)
		
		self.zoom_in1=SpriteNode('typb:Zoom_In')
		self.zoom_in1.position=255,170
		self.zoom_out1=SpriteNode('typb:Zoom_Out')
		self.zoom_out1.position=255,125
		self.map_lock1=SpriteNode('typb:Locked')
		self.map_lock1.position=255,80
		self.add_child(self.zoom_in1)
		self.add_child(self.zoom_out1)
		self.add_child(self.map_lock1)
		
		self.zoom_in2=SpriteNode('typb:Zoom_In')
		self.zoom_in2.position=self.size[0]-255,170
		self.zoom_out2=SpriteNode('typb:Zoom_Out')
		self.zoom_out2.position=self.size[0]-255,125
		self.map_lock2=SpriteNode('typb:Locked')
		self.map_lock2.position=self.size[0]-255,80
		self.add_child(self.zoom_in2)
		self.add_child(self.zoom_out2)
		self.add_child(self.map_lock2)
		
		self.help=SpriteNode('typb:Unknown')
		self.help.position=(40,self.size[1]-40)
		self.add_child(self.help)
			
		self.joypad1touchid = None
		self.joypad2touchid = None
		self.player1maplock = 1
		self.player2maplock = 1
		
		self.dragging1 = False
		self.dragging1_touch = None
		self.dragging1_touchlog = None
		self.dragging1_xyvelocity = None
		
		self.dragging2 = False
		self.dragging2_touch = None
		self.dragging2_touchlog = None
		self.dragging2_xyvelocity = None
		
	def did_change_size(self):
		self.splitscreennode1.crop_rect=(0,0,self.size[0]/2,self.size[1])
		self.splitscreennode2.position=(self.size[0]/2,self.size[1])
		self.splitscreennode2.render_size=(self.size[0]/2,self.size[1])
		self.joypad2.setposition(self.size[0],-1,0,1)
		self.controlpad2.position = (self.size[0]-255,self.joypad2.position[1])
		self.dividernode.setposition(self.size)
		self.zoom_in2.position=self.size[0]-255,170
		self.zoom_out2.position=self.size[0]-255,125
		self.map_lock2.position=self.size[0]-255,80
		self.help.position=(40,self.size[1]-40)
		
	def update(self):
		self.mapnode.player1.z_position = 10000 - self.mapnode.player1.position[1]
		self.mapnode.player2.z_position = 10000 - self.mapnode.player2.position[1]
		
		if self.dragging1_xyvelocity is not None and self.dragging1_touch is None:
			nextpos = self.mapnode.position + self.dragging1_xyvelocity * self.dt
			decay = exp( - self.dt / velocity_decay_timescale_seconds )
			self.dragging1_xyvelocity *= decay
			if ((abs(self.dragging1_xyvelocity[0]) <= min_velocity_points_per_second) and
			    (abs(self.dragging1_xyvelocity[1]) <= min_velocity_points_per_second)):
			    	self.dragging1_xyvelocity = None
			self.mapnode.position = nextpos

		if self.dragging2_xyvelocity is not None and self.dragging2_touch is None:
			nextpos = self.splitscreennode2.render_position + self.dragging2_xyvelocity * self.dt
			decay = exp( - self.dt / velocity_decay_timescale_seconds )
			self.dragging2_xyvelocity *= decay
			if ((abs(self.dragging2_xyvelocity[0]) <= min_velocity_points_per_second) and
			    (abs(self.dragging2_xyvelocity[1]) <= min_velocity_points_per_second)):
			    	self.dragging2_xy_velocity = None
			self.splitscreennode2.render_position = nextpos
									
		if self.joypad1touchid != None and self.t > self.joypad1time:
			px, py, dt = self.joypad1.readout(self.touches[self.joypad1touchid].location)
			if (dt > 0):
				px *= self.mapnode.tile_w
				py *= self.mapnode.tile_h
				self.mapnode.player1.run_action(Action.move_by(px, py, dt))
				if (self.player1maplock == 1):
					self.mapnode.run_action(Action.move_by(-px*self.mapnode.scale, -py*self.mapnode.scale, dt))	
			self.joypad1time = self.t + (dt if dt > 0 else 0.5)

		if self.joypad2touchid != None and self.t > self.joypad2time:
			px, py, dt = self.joypad2.readout(self.touches[self.joypad2touchid].location)
			if (dt > 0):
				px *= self.mapnode.tile_w
				py *= self.mapnode.tile_h
				self.mapnode.player2.run_action(Action.move_by(px, py, dt))
				if (self.player2maplock == 1):
					pass # implement this
			self.joypad2time = self.t + (dt if dt > 0 else 0.5)
			
		# Map2 is a texture that must get generated every update.		
		if (self.player2maplock == 1 and self.splitscreennode2.animating == 0):
			self.splitscreennode2.render_position = (self.mapnode.player2.position[0]-self.size[0]/(4*self.splitscreennode2.scale), self.mapnode.player2.position[1]-self.size[1]/(2*self.splitscreennode2.scale))
		self.splitscreennode2.refresh(self.t)
			
	def touch_began(self, touch):
		if touch.location in self.help.bbox:
			console.alert("Help","Use the joypad to move each player.  Use two fingers on the map to scroll, or use the lock button to lock the position to the player.", "Let's do this", hide_cancel_button = True)
			
		if touch.location in self.zoom_in1.bbox and self.mapnode.scale < mapscaler_max:
			self.mapnode.scale=self.mapnode.scale*mapscaler
			self.mapnode.position = (self.mapnode.position-self.splitscreennode1.size/2)*mapscaler + self.splitscreennode1.size/2
			return
			
		if touch.location in self.zoom_out1.bbox and self.mapnode.scale > mapscaler_min:
			self.mapnode.scale=self.mapnode.scale/mapscaler
			self.mapnode.position = (self.mapnode.position-self.splitscreennode1.size/2)/mapscaler + self.splitscreennode1.size/2
			return	
		
		if touch.location in self.zoom_in2.bbox and self.splitscreennode2.scale < mapscaler_max:
			self.splitscreennode2.scale=self.splitscreennode2.scale*mapscaler
			self.splitscreennode2.render_position += (1-1/mapscaler)*self.splitscreennode2.size/2
			return
			
		if touch.location in self.zoom_out2.bbox and self.splitscreennode2.scale > mapscaler_min:
			self.splitscreennode2.scale=self.splitscreennode2.scale/mapscaler
			self.splitscreennode2.render_position += (1-mapscaler)*self.splitscreennode2.size/2
			return
				
		if touch.location in self.map_lock1.bbox:
			self.player1maplock = not self.player1maplock
			self.map_lock1.texture = Texture('typb:Locked') if self.player1maplock else Texture('typb:Unlocked')
			if (self.player1maplock == 1):
				self.mapnode.run_action(Action.move_to(self.size[0]/4-self.mapnode.player1.position[0]*self.mapnode.scale, self.size[1]/2-self.mapnode.player1.position[1]*self.mapnode.scale, 1.0, TIMING_EASE_IN_OUT))
			return

		if touch.location in self.map_lock2.bbox:
			self.player2maplock = not self.player2maplock
			self.map_lock2.texture = Texture('typb:Locked') if self.player2maplock else Texture('typb:Unlocked')
			if self.player2maplock == 1:
				self.splitscreennode2.move_to((self.mapnode.player2.position[0]-self.size[0]/(4*self.splitscreennode2.scale), self.mapnode.player2.position[1]-self.size[1]/(2*self.splitscreennode2.scale)), self.t, 0.5)
			return				
												
		if (abs(touch.location - self.joypad1.position) < self.joypad1.size[0]/2):
			self.joypad1touchid = touch.touch_id
			self.joypad1time = self.t+0.5
			return

		if (abs(touch.location - self.joypad2.position) < self.joypad2.size[0]/2):
			self.joypad2touchid = touch.touch_id
			self.joypad2time = self.t+0.5
			return
											
		if touch.location in self.splitscreennode1.crop_rect:	
			if self.dragging1_touch is None:
				self.dragging1_touch = touch.touch_id
				self.dragging1_xyvelocity = None
			else: # Only enable map dragging if there is a second touch
				self.dragging1 = True
				self.dragging1_touchlog = []
				self.player1maplock = 0
				self.map_lock1.texture = Texture('typb:Unlocked')	
				
		if touch.location in self.splitscreennode2.bbox:
			if self.dragging2_touch is None:
				self.dragging2_touch = touch.touch_id
				self.dragging2_xyvelocity = None
			else: # Only enable map dragging if there is a second touch
				self.dragging2 = True
				self.dragging2_touchlog = []
				self.player2maplock = 0
				self.map_lock2.texture = Texture('typb:Unlocked')	
			
	def touch_moved(self, touch):
		if touch.touch_id == self.dragging1_touch and self.dragging1:
			self.dragging1_touchlog.append((datetime.datetime.utcnow(), touch.location))
			self.dragging1_touchlog = self.dragging1_touchlog[-max_retained_touch_points:]
			self.mapnode.position += touch.location - touch.prev_location
			self.touch_time=self.t
		
		if touch.touch_id == self.dragging2_touch and self.dragging2:
			self.dragging2_touchlog.append((datetime.datetime.utcnow(), touch.location))
			self.dragging2_touchlog = self.dragging2_touchlog[-max_retained_touch_points:]
			self.splitscreennode2.render_position-=(touch.location-touch.prev_location)/self.splitscreennode2.scale
			self.dragging2_touch_time=self.t			
			
	def touch_ended(self, touch):
		if touch.touch_id == self.dragging1_touch:
			self.dragging1_touch = None
			if self.dragging1 == True:
				self.dragging1 = False
				self.dragging1_xyvelocity = None
				if len(self.dragging1_touchlog) >= 2:
					dt = (self.dragging1_touchlog[-1][0] - self.dragging1_touchlog[0][0]).total_seconds()
					if dt > 0:
						x_velocity = (self.dragging1_touchlog[-1][1].x - self.dragging1_touchlog[0][1].x) / dt
						y_velocity = (self.dragging1_touchlog[-1][1].y - self.dragging1_touchlog[0][1].y) / dt
						self.dragging1_xyvelocity = Vector2(x_velocity, y_velocity)
			
		if touch.touch_id == self.dragging2_touch:
			self.dragging2_touch = None
			if self.dragging2 == True:
				self.dragging2 = False
				self.dragging2_xyvelocity = None
				if len(self.dragging2_touchlog) >= 2:
					dt = (self.dragging2_touchlog[-1][0] - self.dragging2_touchlog[0][0]).total_seconds()
					if dt > 0:
						x_velocity = - (self.dragging2_touchlog[-1][1].x - self.dragging2_touchlog[0][1].x) / dt
						y_velocity = - (self.dragging2_touchlog[-1][1].y - self.dragging2_touchlog[0][1].y) / dt
						self.dragging2_xyvelocity = Vector2(x_velocity, y_velocity)/self.splitscreennode2.scale
						
		if touch.touch_id == self.joypad1touchid:
			self.joypad1touchid = None
			self.joypad1.indicator((0,0))
			
		if touch.touch_id == self.joypad2touchid:
			self.joypad2touchid = None
			self.joypad2.indicator((0,0))
		
		
if __name__ == '__main__':
	s=MyScene()
	run(s, show_fps=True)

