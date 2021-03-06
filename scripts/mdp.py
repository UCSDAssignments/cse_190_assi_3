from read_config import read_config
from cse_190_assi_3.msg import *
from copy import deepcopy
import rospy

class MDP():
	BLANK, GOAL, START, OBSTACLE, PIT = range(5)

	def __init__(self):
		self.json_data = read_config()
		self.create_map()
		self.create_pub()
		self.action_list = ["N","W","E","S"] 		
		self.mdp()

	def mdp(self):
		
		for k in range(self.max_iter):
			new_map = deepcopy(self.value_map)
			for idx_r, row in enumerate(self.value_map):
				for idx_c, curr_val in enumerate(row):
					cell_state = self.map[idx_r][idx_c]
					if cell_state == MDP.GOAL:
						self.policy_map[idx_r][idx_c] = "GOAL"
						continue
					elif cell_state == MDP.OBSTACLE:
						self.policy_map[idx_r][idx_c] = "WALL"
						continue
					elif cell_state == MDP.PIT:
						self.policy_map[idx_r][idx_c] = "PIT"
						continue

					max_act_list = []
					curr_state = (idx_r,idx_c)
					possible_moves = self.get_next_states(curr_state)
					for intended_act in possible_moves:
						total = 0.0
						for action, next_state in possible_moves.items():
							prob = self.get_prob(action,intended_act)
							reward = self.get_reward(curr_state, next_state)
							prev_state_util = self.value_map[next_state[0]][next_state[1]]
							total += prob * (reward + self.discount_factor *
								prev_state_util)
						max_act_list.append((total, intended_act))
				
					total,direction = max(max_act_list, key=lambda x: x[0])
					new_map[idx_r][idx_c] = total
					self.policy_map[idx_r][idx_c] = direction
			
			policy_list = self.flatten_2dlist(self.policy_map)
			policy_data = PolicyList()
			policy_data.data = policy_list
			rospy.sleep(1.5)
			self.policylist_pub.publish(policy_data)
			
			if self.converged(new_map):
				return
			self.value_map =  deepcopy(new_map)

	def flatten_2dlist(self, new_map):
		new_list = []
		for row in new_map:
			for col in row:
				new_list.append(col)
		return new_list

	def get_prob(self,action,intended_act):
		prob = 0.0
		if action == intended_act:
			prob = self.forward_pb
		elif intended_act == self.get_oppo_action(action):
			prob = self.back_pb
		elif action == self.get_right_of_action(intended_act):
			prob = self.right_pb
		else:
			prob = self.left_pb
		return prob

	def get_oppo_action(self,action):
		oppo_dict = {"S":"N", "N":"S", "E":"W", "W":"E"}
		return oppo_dict[action]

	def get_right_of_action(self,intended_action):
		oppo_dict = {"W":"N", "E":"S", "N":"E", "S":"W"}
		return oppo_dict[intended_action]

	'''def get_left_of_action(self,intended_action):
		oppo_dict = {"W":"S", "E":"N", "N":"W", "S":"E"}
		return oppo_dict[intended_action]'''

	def get_reward(self,curr_state, next_state):
		reward = 0
		if self.map[next_state[0]][next_state[1]] == MDP.OBSTACLE  or curr_state == next_state:
			reward += self.wallhit_rw
		elif self.map[next_state[0]][next_state[1]] == MDP.PIT:
			reward += self.fallpit_rw
			reward += self.step_rw
		elif self.map[next_state[0]][next_state[1]] == MDP.GOAL:
			reward += self.reachedgoal_rw
			reward += self.step_rw
		else:
			reward += self.step_rw
		return reward

	def get_next_states(self,curr_state):
		next_states = {}

		#move_list is sorted at this point in N,W,E,S order
		for idx,move in enumerate(self.move_list):
			policy = ""

			next_state = (curr_state[0]+move[0], curr_state[1]+move[1])
			if (next_state[0] < 0 or next_state[0] >= len(self.map) or next_state[1] < 0 or
				next_state[1] >= len(self.map[0])):
				next_states[self.action_list[idx]] = curr_state
				continue

			map_val = self.map[next_state[0]][next_state[1]]
			
			if map_val == MDP.OBSTACLE:
				next_states[self.action_list[idx]] = curr_state
			else:
				next_states[self.action_list[idx]] = next_state
		return next_states

	def converged(self, newmap):
		res = []
		for idx_r, row in enumerate(newmap):
			for idx_c, curr_val in enumerate(row):
				prev_val = self.value_map[idx_r][idx_c]
				if abs(curr_val - prev_val) < self.thres:
					res.append(True)
				else:
					res.append(False)

		return all(res)

	def create_map(self):
		map_size = self.json_data["map_size"]
		self.map = [[MDP.BLANK for c in range(map_size[1])] for r in range(map_size[0])]
		self.policy_map = [["" for c in range(map_size[1])] for r in range(map_size[0])]
		self.value_map = deepcopy(self.map)
	
		self.step_rw = self.json_data["reward_for_each_step"]
		self.wallhit_rw = self.json_data["reward_for_hitting_wall"]
		self.fallpit_rw = self.json_data["reward_for_falling_in_pit"]
		self.reachedgoal_rw = self.json_data["reward_for_reaching_goal"]

		self.max_iter = self.json_data["max_iterations"]
		self.thres = self.json_data["threshold_difference"]
		self.discount_factor = self.json_data["discount_factor"]

		self.forward_pb = self.json_data["prob_move_forward"]
		self.back_pb = self.json_data["prob_move_backward"]
		self.left_pb = self.json_data["prob_move_left"]
		self.right_pb = self.json_data["prob_move_right"]

		self.start = self.json_data["start"]
		self.move_list = self.json_data["move_list"]
		self.move_list.sort()
		
		self.goal = self.json_data["goal"]
		self.map[self.goal[0]][self.goal[1]] = MDP.GOAL
		self.map[self.start[0]][self.start[1]] = MDP.START

		self.value_map[self.goal[0]][self.goal[1]] = self.reachedgoal_rw

		for wall_r,wall_c in self.json_data["walls"]:
			self.map[wall_r][wall_c] = MDP.OBSTACLE
			self.value_map[wall_r][wall_c] = self.wallhit_rw
		
		for pit_r, pit_c in self.json_data["pits"]:
			self.map[pit_r][pit_c] = MDP.PIT
			self.value_map[pit_r][pit_c] = self.fallpit_rw


	def create_pub(self):
		self.policylist_pub = rospy.Publisher("/results/policy_list", PolicyList,
			queue_size=10)

if __name__ == "__main__":
	MDP()
