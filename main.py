import itertools
import random

import hw3
import sample_agent
from copy import deepcopy
import time

CONSTRUCTOR_TIMEOUT = 60
ACTION_TIMEOUT = 5
DIMENSIONS = (10, 10)
PENALTY = 1000


def pad_the_input(a_map):
    state = {}
    new_i_dim = DIMENSIONS[0] + 2
    new_j_dim = DIMENSIONS[1] + 2
    for i in range(0, new_i_dim):
        for j in range(0, new_j_dim):
            if i == 0 or j == 0 or i == new_i_dim - 1 or j == new_j_dim - 1:
                state[(i, j)] = 'U'
            elif 'S' in a_map[i - 1][j - 1]:
                state[(i, j)] = 'S1'
            else:
                state[(i, j)] = a_map[i - 1][j - 1]
    return state


class Game:
    def __init__(self, a_map):
        self.ids = [hw3.ids, sample_agent.ids]
        self.initial_state = pad_the_input(a_map)
        self.state = deepcopy(self.initial_state)
        self.control_zone_1 = None
        self.control_zone_2 = None
        self.divide_map()
        self.score = [0, 0]
        self.agents = []

    def state_to_agent(self):
        state_as_list = []
        for i in range(DIMENSIONS[0]):
            state_as_list.append([]*DIMENSIONS[1])
            for j in range(DIMENSIONS[1]):
                state_as_list[i].append(self.state[(i + 1, j + 1)][0])
        return state_as_list

    def initiate_agent(self, module, control_zone, first):
        start = time.time()
        control_zone_to_agent = [(i - 1, j - 1) for (i, j) in control_zone]
        agent = module.Agent(self.state_to_agent(), control_zone_to_agent, first)
        if time.time() - start > CONSTRUCTOR_TIMEOUT:
            self.handle_constructor_timeout(module.ids)
        return agent

    def divide_map(self):
        habitable_tiles = [(i, j) for i, j in
                           itertools.product(range(1, DIMENSIONS[0] + 1),
                                             range(1, DIMENSIONS[1] + 1)) if 'U' not in self.state[(i, j)]]
        random.shuffle(habitable_tiles)

        half = len(habitable_tiles) // 2
        self.control_zone_1 = set(habitable_tiles[:half])
        self.control_zone_2 = set(habitable_tiles[half:])
        assert len(self.control_zone_1) == len(self.control_zone_2)

    def get_action(self, agent):
        action = agent.act(self.state_to_agent())
        return action

    def check_if_action_legal(self, action, zone_of_control):
        if not action:
            return False
        if len(action) > 3:
            return False
        count = {'vaccinate': 0, 'quarantine': 0}
        for atomic_action in action:
            effect, location = atomic_action[0], (atomic_action[1][0] + 1, atomic_action[1][1] + 1)
            try:
                status = self.state[location]
            except KeyError:
                return False
            if effect.lower() not in ['vaccinate', 'quarantine']:
                return False
            count[effect] += 1
            if count['vaccinate'] > 1 or count['quarantine'] > 2:
                return False
            if effect == 'vaccinate' and 'H' not in status:
                return False
            if effect == 'quarantine' and 'S' not in status:
                return False
            if location not in zone_of_control:
                return False

        return True

    def apply_action(self, actions):
        for atomic_action in actions:
            effect, location = atomic_action[0], (atomic_action[1][0] + 1, atomic_action[1][1] + 1)
            if 'v' in effect:
                self.state[location] = 'I'
            else:
                self.state[location] = 'Q0'

    def change_state(self):
        new_state = deepcopy(self.state)

        # virus spread
        for i in range(1, DIMENSIONS[0] + 1):
            for j in range(1, DIMENSIONS[1] + 1):
                if self.state[(i, j)] == 'H' and ('S' in self.state[(i - 1, j)] or
                                                  'S' in self.state[(i + 1, j)] or
                                                  'S' in self.state[(i, j - 1)] or
                                                  'S' in self.state[(i, j + 1)]):
                    new_state[(i, j)] = 'S1'

        # advancing sick counters
        for i in range(1, DIMENSIONS[0] + 1):
            for j in range(1, DIMENSIONS[1] + 1):
                if 'S' in self.state[(i, j)]:
                    turn = int(self.state[(i, j)][1])
                    if turn < 3:
                        new_state[(i, j)] = 'S' + str(turn + 1)
                    else:
                        new_state[(i, j)] = 'H'

                # advancing quarantine counters
                if 'Q' in self.state[(i, j)]:
                    turn = int(self.state[(i, j)][1])
                    if turn < 2:
                        new_state[(i, j)] = 'Q' + str(turn + 1)
                    else:
                        new_state[(i, j)] = 'H'

        self.state = new_state

    def update_scores(self, player, control_zone):
        for (i, j) in control_zone:
            if 'H' in self.state[(i, j)]:
                self.score[player] += 1
            if 'I' in self.state[(i, j)]:
                self.score[player] += 1
            if 'S' in self.state[(i, j)]:
                self.score[player] -= 1
            if 'Q' in self.state[(i, j)]:
                self.score[player] -= 5

    def handle_constructor_timeout(self, agent):
        raise Exception

    def get_legal_action(self, number_of_agent, zoc):
        start = time.time()
        action = self.get_action(self.agents[number_of_agent])
        finish = time.time()
        if finish - start > ACTION_TIMEOUT:
            self.score[number_of_agent] -= PENALTY
            print(f'agent of {self.ids[number_of_agent]} timed out on action!')
            return []
        if not self.check_if_action_legal(action, zoc):
            self.score[number_of_agent] -= PENALTY
            print(f'agent of {self.ids[number_of_agent]} chose illegal action!')
            return []
        return action

    def play_episode(self, swapped=False):

        while 'S1' in self.state.values() or 'S2' in self.state.values() or 'S3' in self.state.values():

            obs_state = self.state_to_agent()
            for line in obs_state:
                print(line)
            print()

            if not swapped:
                action = self.get_legal_action(0, self.control_zone_1)
                if not action:
                    return
                self.apply_action(action)
                print(f'player {self.ids[0]} uses {action}!')

                action = self.get_legal_action(1, self.control_zone_2)
                if not action:
                    return
                self.apply_action(action)
                print(f'player {self.ids[1]} uses {action}!')
            else:
                action = self.get_legal_action(1, self.control_zone_1)
                if not action:
                    return
                self.apply_action(action)
                print(f'player {self.ids[1]} uses {action}!')

                action = self.get_legal_action(0, self.control_zone_2)
                if not action:
                    return
                self.apply_action(action)
                print(f'player {self.ids[0]} uses {action}!')

            self.change_state()
            if not swapped:
                self.update_scores(0, self.control_zone_1)
                self.update_scores(1, self.control_zone_2)
            else:
                self.update_scores(1, self.control_zone_1)
                self.update_scores(0, self.control_zone_2)
            print('------')

    def play_game(self):
        print(f'***********  starting a first round!  ************ \n \n')
        self.agents = [self.initiate_agent(hw3, self.control_zone_1, 'first'),
                       self.initiate_agent(sample_agent, self.control_zone_2, 'second')]
        self.play_episode()

        print(f'***********  starting a second round!  ************ \n \n')
        self.state = deepcopy(self.initial_state)

        self.agents = [self.initiate_agent(hw3, self.control_zone_2, 'second'),
                       self.initiate_agent(sample_agent, self.control_zone_1, 'first')]

        self.play_episode(swapped=True)
        print(f'end of game!')
        return self.score


def main():
    a_map = [
        ['H', 'S', 'S', 'H', 'H', 'H', 'U', 'S', 'H', 'H'],
        ['H', 'H', 'H', 'H', 'H', 'H', 'H', 'H', 'H', 'H'],
        ['H', 'U', 'U', 'H', 'H', 'U', 'H', 'H', 'H', 'H'],
        ['H', 'H', 'U', 'H', 'S', 'U', 'H', 'H', 'U', 'H'],
        ['H', 'H', 'U', 'H', 'H', 'U', 'H', 'H', 'S', 'H'],
        ['S', 'H', 'H', 'H', 'H', 'H', 'H', 'H', 'H', 'H'],
        ['H', 'H', 'H', 'S', 'U', 'U', 'H', 'H', 'H', 'U'],
        ['H', 'U', 'H', 'H', 'U', 'H', 'H', 'H', 'U', 'H'],
        ['H', 'H', 'U', 'H', 'H', 'U', 'H', 'S', 'U', 'H'],
        ['H', 'H', 'H', 'H', 'S', 'H', 'H', 'H', 'H', 'H'],
    ]
    assert len(a_map) == DIMENSIONS[0]
    assert len(a_map[0]) == DIMENSIONS[1]
    game = Game(a_map)
    results = game.play_game()
    print(f'Score for {hw3.ids} is {results[0]}, score for {sample_agent.ids} is {results[1]}')


if __name__ == '__main__':
    main()
