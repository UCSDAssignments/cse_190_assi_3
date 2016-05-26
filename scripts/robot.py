#!/usr/bin/env python
from astar import AStar
from mdp import MDP
from std_msgs.msg import Bool
import rospy

class RobotLocalizer():
	def __init__(self):
		rospy.init_node("robot_node", anonymous=True)
		self.out_file_pub = rospy.Publisher("/map_node/sim_complete", Bool,
			queue_size=10)
		AStar()
		MDP()
		self.out_file_pub.publish(Bool(data=True))
		rospy.sleep(1)
		rospy.signal_shutdown("All Done.")
		
if __name__ == "__main__":
	try:
		RobotLocalizer()
	except rospy.ROSInterruptException:
		pass
		
